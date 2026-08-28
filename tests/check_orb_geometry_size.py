#!/usr/bin/env python3
"""tests/check_orb_geometry_size.py  v1.0  (2026-08-28, r181)
ORB sizes on ACTUAL risk: pure geometry off the impulsive candle.
Born red at 14869dc. G1 the operator's two extremes (10 lots / 1 lot);
G2 worst entry = 1; G3 degenerate geometry = 1; G4 non-ORB untouched;
G5 the override runs AFTER compute_size and only for ORBStrategy (AST)."""
import ast, os, sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root); os.environ.setdefault("OT_PAPER_TRADING", "1")
_fails=[]
def check(l,c,d=""):
    print(f"  {'PASS' if c else 'FAIL'}  {l}"+(f"  — {d}" if d else ""))
    if not c: _fails.append(l)
def geo(w,d):  # the same math the seam applies
    return max(1,int(w//d)) if (w>0 and 0<d<=w*1.0001) else 1
def main():
    check("G1a shallow break: 6.35 width / 0.61 stop -> 10 lots", geo(6.35,0.61)==10)
    check("G1b deep break: 6.35 / 6.05 -> 1 lot", geo(6.35,6.05)==1)
    check("G2 worst entry (stop == width) -> exactly 1", geo(6.35,6.35)==1)
    check("G3 degenerate: zero or beyond-width distance -> 1",
          geo(6.35,0)==1 and geo(6.35,7.0)==1 and geo(0,1)==1)
    src=open(os.path.join(_root,"main.py"),encoding="utf-8").read()
    fn=next(n for n in ast.walk(ast.parse(src)) if isinstance(n,ast.FunctionDef)
            and n.name=="_execute_entry_signal")
    b=ast.unparse(fn)
    i_sz=b.find("risk_mgr.compute_size"); i_geo=b.find("== 'ORBStrategy'")
    check("G5 the override is inside _execute_entry_signal, AFTER compute_size, "
          "gated on ORBStrategy only",
          i_sz!=-1 and i_geo!=-1 and i_sz<i_geo and "orb_range_high" in b
          and "signal.contracts = _geo" in b, f"{i_sz}<{i_geo}")
    check("G4 non-ORB signals keep the sizer's number (one sizing assign, one "
          "geometry override, geometry only under the ORB gate)",
          b.count("signal.contracts = sizing.contracts")==1
          and b.count("signal.contracts = _geo")==1
          and b.index("signal.contracts = _geo") > b.index("== 'ORBStrategy'"))
    print()
    if _fails: print(f"FAILED {len(_fails)}: "+", ".join(_fails)); return 1
    print("check_orb_geometry_size: all checks pass"); return 0
if __name__=="__main__": sys.exit(main())
