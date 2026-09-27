// OpenSCAD text echo normally emits six significant digits. Split numeric
// values into an integer and two six-digit fraction groups before exporting.
// This is a transport codec, not a second source for geometric parameters.
function cc_pack(v)=is_num(v)?let(i=floor(v),f=v-i,m=floor(f*1000000))
    ["__f12__",i,m,floor(f*1000000000000)-m*1000000]:
    is_list(v)?[for(x=v)cc_pack(x)]:v;
