use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-output-interface.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-housing-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/feeder-return-spring.scad>

function ac_pad6(x)=let(s=str(x))str(len(s)<6?"0":"",len(s)<5?"0":"",len(s)<4?"0":"",len(s)<3?"0":"",len(s)<2?"0":"",s);
function ac_num(x)=assert(abs(x)<100000,"Contract number too large for fixed-decimal encoder")let(a=abs(x),i=floor(a),f=round((a-i)*1000000000000),carry=floor(f/1000000000000),v=f-carry*1000000000000)str(x<0?"-":"",i+carry,".",ac_pad6(floor(v/1000000)),ac_pad6(v%1000000));
function ac_escape(s,i=0)=i>=len(s)?"":str(s[i]=="\\"?"\\\\":s[i]=="\""?"\\\"":s[i]=="\n"?"\\n":s[i]=="\r"?"\\r":s[i]=="\t"?"\\t":s[i],ac_escape(s,i+1));
function ac_join(a,i=0)=i>=len(a)?"":str(i>0?",":"",ac_json(a[i]),ac_join(a,i+1));
function ac_json(x)=is_undef(x)?"null":is_bool(x)?(x?"true":"false"):is_num(x)?ac_num(x):is_string(x)?str("\"",ac_escape(x),"\""):is_list(x)?str("[",ac_join(x),"]"):assert(false,"Unsupported contract value");

echo("ACTUATION_JSON",ac_json([["input",ci_spec()],["output",co_contract_data()],["route",cr_contract()],["spring_length_rest",rs_L(0)],["spring_length_pulled",rs_L(1)]]));
