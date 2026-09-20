"""Summarize this application's private ledger without making network calls."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

def summarize(source, destination):
    groups = defaultdict(lambda: {"calls":0,"success":0,"failed":0,
        "input_tokens":0,"output_tokens":0,"total_tokens":0,
        "missing_input_tokens":0,"missing_output_tokens":0,"missing_total_tokens":0})
    seen = {}
    for line in Path(source).read_text(encoding="utf-8").splitlines():
        record=json.loads(line)
        uid=record["call_id"]
        if uid in seen:
            if seen[uid] != record: raise ValueError("Conflicting call ID: "+uid)
            continue
        seen[uid]=record
        group=groups[(record["model"],record["key_suffix"],record["purpose"])]
        group["calls"]+=1
        group["success" if record["ok"] else "failed"]+=1
        for name in ("input_tokens","output_tokens","total_tokens"):
            value=record.get(name)
            if isinstance(value,int): group[name]+=value
            else: group["missing_"+name]+=1
    rows=[dict(model=k[0],key_suffix=k[1],purpose=k[2],**v) for k,v in groups.items()]
    out=Path(destination);out.mkdir(parents=True,exist_ok=True)
    (out/"usage_summary.json").write_text(json.dumps({"calls":len(seen),"groups":rows,
        "note":"Missing token usage is unknown, not zero. No monetary costs are inferred."},indent=2))
    if rows:
        with (out/"usage_by_model_key_purpose.csv").open("w",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    else:
        (out/"usage_by_model_key_purpose.csv").write_text("model,key_suffix,purpose,calls\n")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--log",default=str(Path(__file__).parent/"private/yibu_api_calls.jsonl"))
    parser.add_argument("--out-dir",default=str(Path(__file__).parent/"private/summary"))
    args=parser.parse_args()
    if not Path(args.log).exists(): parser.exit(message="No ledger exists: no recorded API calls. Do not fabricate usage.\n")
    summarize(args.log,args.out_dir)
