import pandas as pd
ms_files = {
    '여주시': '/Users/galaxy/anti_codebase/여주시 MS.xlsx',
    '이천시': '/Users/galaxy/anti_codebase/이천시 MS.xlsx',
    '제천시': '/Users/galaxy/anti_codebase/제천시 MS.xlsx',
    '충주시': '/Users/galaxy/anti_codebase/충주시 MS.xlsx'
}
for city, path in ms_files.items():
    df = pd.read_excel(path)
    c_col = df.columns[0]
    last_week = df.columns[-1]
    df[c_col] = df[c_col].astype(str).str.strip()
    
    gcoo = df[df[c_col] == '지쿠']
    gcoo_ms = gcoo[last_week].values[0] if not gcoo.empty else 0
    
    others = df[df[c_col] != '지쿠']
    top_c = others.sort_values(by=last_week, ascending=False).iloc[0]
    print(f"{city}: 지쿠={gcoo_ms:.1f}%, 1위={top_c[c_col]}({top_c[last_week]:.1f}%)")
