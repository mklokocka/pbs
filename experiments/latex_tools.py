"""Toolkit for LaTeX presentation of results.

This module provides helpful functions for parsing results from `ltlcross_runner`
to the LaTeX format in the form of different graphs.

Taken from https://github.com/xblahoud/LTL2DA-comparison/blob/master/Comparison.ipynb.

"""
import pandas as pd


tool_names = {
    'pbs': '\\PBS',
    'ba_via_det': 'Spot~(BA)',
    'tgba_via_det': 'Spot~(TGBA)',
    'spot_ncsb': '\\NCSB'
}


def fix_tools(tool):
    return tool_names.get(tool, tool)


def sc_plot(r,t1,t2,filename=None,include_equal = True,col='states',log=None,size=(7,6.5),kw=None,clip=None, add_count=True):
    merged = isinstance(r,list)
    if merged:
        vals = pd.concat([run.values[col] for run in r])
        vals.index = vals.index.droplevel(0)
        vals = vals.groupby(vals.index).first()
    else:
        vals = r.values[col]
    to_plot = vals.loc(axis=1)[[t1,t2]] if include_equal else\
        vals[vals[t1] != vals[t2]].loc(axis=1)[[t1,t2]]
    to_plot['count'] = 1
    to_plot.dropna(inplace=True)
    to_plot = to_plot.groupby([t1,t2]).count().reset_index()
    if filename is not None:
        print(scatter_plot(to_plot, log=log, size=size,kw=kw,clip=clip, add_count=add_count),file=open(filename,'w'))
    else:
        return scatter_plot(to_plot, log=log, size=size,kw=kw,clip=clip, add_count=add_count)


def scatter_plot(df, short_toolnames=True, log=None, size=(7,6.5),kw=None,clip=None,add_count = True):
    t1, t2, _ = df.columns.values
    if short_toolnames:
        t1 = fix_tools(t1.split('.')[0])
        t2 = fix_tools(t2.split('.')[0])
    vals = ['({},{}) [{}]\n'.format(v1,v2,c) for v1,v2,c in df.values]
    plots = '''\\addplot[
    scatter, scatter src=explicit, 
    only marks, fill opacity=0.5,
    draw opacity=0] coordinates
    {{{}}};'''.format(' '.join(vals))
    start_line = 0 if log is None else 1
    line = '\\addplot[darkgreen,domain={}:{}]{{x}};'.format(start_line, min(df.max(axis=0)[:2])+1)
    axis = 'axis'
    mins = 'xmin=0,ymin=0,'
    clip_str = ''
    if clip is not None:
        clip_str = '\\draw[red,thick] ({},{}) rectangle ({},{});'.format(*clip)
    if log:
        if log == 'both':
            axis = 'loglogaxis'
            mins = 'xmin=1,ymin=1,'
        else:
            axis = 'semilog{}axis'.format(log)
            mins = mins + '{}min=1,'.format(log)
    args = ''
    if kw is not None:
        if 'title' in kw and add_count:
            kw['title'] = '{{{} [{}]}}'.format(kw['title'],df['count'].sum())
        args = ['{}={},\n'.format(k,v) for k,v in kw.items()]
        args = ''.join(args)
    res = '''\\begin{{tikzpicture}}
\\pgfplotsset{{every axis legend/.append style={{
cells={{anchor=west}},
draw=none,
}}}}
\\pgfplotsset{{colorbar/width=.3cm}}
\\pgfplotsset{{title style={{align=center,
                        font=\\small}}}}
\\pgfplotsset{{compat=1.14}}
\\begin{{{0}}}[
{1}
colorbar,
%thick,
axis x line* = bottom,
axis y line* = left,
width={2}cm, height={3}cm, 
xlabel={{{4}}},
ylabel={{{5}}},
cycle list={{%
{{darkgreen, solid}},
{{blue, densely dashed}},
{{red, dashdotdotted}},
{{brown, densely dotted}},
{{black, loosely dashdotted}}
}},
{6}%
]
{7}%
{8}%
{9}%
\\end{{{0}}}
\\end{{tikzpicture}}
'''.format(axis,mins,
                    size[0],size[1],t1,t2,
                    args,plots,line,
                    clip_str)
    return res
