import pandas as pd
import numpy as np
from pandas import DataFrame
from decimal import *

PRICE_INDEX_BASE_YEAR = 2013

DIRECTORY = 'data/'
TAX_BREAK_RAW = '%stax-break-raw.csv' % DIRECTORY
GDP = '%shist10z1.xls' % DIRECTORY
TAX_BREAK_COMPLETE = '%stax-break-complete.csv' % DIRECTORY
TAX_BREAK_COMPLETE_CBO = '%stax-break-complete-combined-for-cbo.csv' % DIRECTORY
 
def clean_text(text, required=True):
    if required and pd.isnull(text):
        print 'a row is missing text data!'
        return ' '
    elif pd.isnull(text):
        return ' '
    text = text.strip()
    if text[-1] == ':':
        return text[0:-1].title()
    else:
        return text.title()

def clean_year(x):
    try:
        return int(x[:4])
    except:
        return np.nan

def clean_amount(amount):
    try:
        return float(str(amount).replace(',','')) * 1000000
    except:
        if pd.notnull(amount):
            print 'invalid amount changed to NaN: %s' % amount
        return np.nan

def tweak_name(x):
    new_name = x.replace(' (Normal Tax Method)', '')
    return new_name

def get_total(row):
    #in 1981 and 1982, data are not broken out by corp/indv
    if row['year'] == 1981 or row['year'] == 1982:
        return row['total8182']

    #make sure the NaNs don't null out the totals
    if pd.isnull(row['corp']) and pd.isnull(row['indv']):
        return np.nan
    elif pd.isnull(row['corp']):
        return row['indv']
    elif pd.isnull(row['indv']):
        return row['corp']
    else:
        return row['indv'] + row['corp']

def percent_change(row):
    try:
        last_year = te[(te.year == row['year']-1) & 
            (te.name == row['name'])].reset_index()['total_adj'][0]
        if last_year == 0:
            return np.nan
        else:
            return (row['total_adj'] - last_year) / last_year * 100
    except:
        return np.nan

def round_dollar(x):
    if pd.notnull(x):
        return Decimal(x).quantize(Decimal('1.'),
        rounding=ROUND_HALF_DOWN)
    else:
        return x

def round_percent(x):
    if pd.notnull(x):
        return Decimal(x).quantize(Decimal('1.00'),
            rounding=ROUND_HALF_DOWN)
    else:
        return x

# Using annual estimates created by Treasury and 
# reported by OMB in the annual president's budget request, create
# normalized time-series dataset of tax break estimated costs.

gdpFile = pd.ExcelFile(GDP)
gdp = gdpFile.parse(gdpFile.sheet_names[0], index_col=None, parse_cols=2)
gdp.columns = ['year', 'gdp', 'gdp_price_index']
gdp['year'] = gdp['year'].map(lambda x: clean_year(x))
gdp = gdp.dropna(subset=['year'])
gdp.year = gdp.year.astype(np.int64)

ter = pd.read_csv(
    TAX_BREAK_RAW,
    header=None,
    index_col=False,
    usecols=[0,1,2,3,4,5,6,7],
    skiprows=1,
    names=['npp_cat', 'omb_cat', 'name', 'year', 'orig_name', 'corp', 'indv', 'total8182']
)
te = ter

#drop any rows with a missing year (should not happen!)
missing_years = len(te[te['year'].isnull()].index)
if missing_years > 0:
    print 'dropping %s rows with missing year' % missing_years
    te = te.dropna(subset=['year'])
te.year = te.year.astype(np.int64)

#strip leading/trailing whitespace from incoming text fields
te['name'] = te['name'].apply(lambda x: clean_text(x))
te['npp_cat'] = te['npp_cat'].apply(lambda x: clean_text(x))
te['omb_cat'] = te['omb_cat'].apply(lambda x: clean_text(x))
te['orig_name'] = te['orig_name'].apply(lambda x: clean_text(x,False))

#tweak content of tax break names 
te['name'] = te['name'].apply(lambda x: tweak_name(x))

#make sure incoming corp. and indv. amounts are either missing or numeric
te['indv'] = te['indv'].apply(lambda x: clean_amount(x))
te['corp'] = te['corp'].apply(lambda x: clean_amount(x))
te['total8182'] = te['total8182'].apply(lambda x: clean_amount(x))
te['total'] = te.apply(lambda row: get_total(row), axis=1)

#merge in deflators and add inflation-adjusted columns
te = pd.merge(te, gdp, on='year', how='left')
file_base_year = gdp[gdp['gdp_price_index']==1]['year'].reset_index(
    drop=True)[0]
if file_base_year <> PRICE_INDEX_BASE_YEAR:
    print 'GDP Price Index base year is %s on OMB file.' % file_base_year
    print 'Adjusting to use %s instead.' % PRICE_INDEX_BASE_YEAR
    denom = gdp[gdp['year']==PRICE_INDEX_BASE_YEAR].reset_index(
        drop=True)['gdp_price_index'][0]
    te['gdp_price_index'] = te['gdp_price_index']/denom

te['gdp'] = te['gdp'].map(lambda x: x * 1000000000) #incoming gdp in billions
te['corp_adj'] = te['corp'] / te['gdp_price_index']
te['indv_adj'] = te['indv'] / te['gdp_price_index']
te['total_adj'] = te['total'] / te['gdp_price_index']

#create Series of totals to use for calculating percentages
year_total = te['total'].groupby(te['year']).sum()
npp_cat_total = te['total'].groupby([te['year'],te['npp_cat']]).sum()
omb_cat_total = te['total'].groupby([te['year'],te['omb_cat']]).sum()
corp_total = te['corp'].groupby(te['year']).sum()
indv_total = te['indv'].groupby(te['year']).sum()

#add percentage columns
te = te.merge(te.apply(lambda row: pd.Series({
    'percent_total':row['total']/year_total[row['year']]*100,
    'percent_corp':row['corp']/corp_total[row['year']]*100,
    'percent_indv':row['indv']/indv_total[row['year']]*100,
    'percent_gdp':row['total']/row['gdp']*100,
    'percent_npp_cat':row['total']/npp_cat_total[row['year'],row['npp_cat']]*100,
    'percent_omb_cat':row['total']/omb_cat_total[row['year'],row['omb_cat']]*100
    }),axis=1),left_index=True, right_index=True)
te['percent_change'] = te.apply(lambda row: percent_change(row), axis=1)

#finally, round everything
te['corp_adj'],te['indv_adj'],te['total_adj'] = (
    te['corp_adj'].map(lambda x: round_dollar(x)),
    te['indv_adj'].map(lambda x: round_dollar(x)),
    te['total_adj'].map(lambda x: round_dollar(x))
    )

te['percent_corp'], te['percent_gdp'], te['percent_indv'], te['percent_npp_cat'], te['percent_omb_cat'], te['percent_total'], te['percent_change'] = (
    te['percent_corp'].map(lambda x: round_percent(x)),
    te['percent_gdp'].map(lambda x: round_percent(x)),
    te['percent_indv'].map(lambda x: round_percent(x)),
    te['percent_npp_cat'].map(lambda x: round_percent(x)),
    te['percent_omb_cat'].map(lambda x: round_percent(x)),
    te['percent_total'].map(lambda x: round_percent(x)),
    te['percent_change'].map(lambda x: round_percent(x))
)

del te['total8182']
te.sort(['year','name'], inplace=True)
te.to_csv('%s' % TAX_BREAK_COMPLETE, index=False,
    cols = ['omb_cat','name','year', 'corp', 'indv', 'total', 'gdp', 'gdp_price_index', 
    'corp_adj', 'indv_adj', 'total_adj', 'percent_corp', 'percent_gdp',
    'percent_indv', 'percent_omb_cat', 'percent_total', 'percent_change', 'orig_name'])

# Create a second time series of tax break estimates. This one 
# groups a few individual tax breaks as reported by Treasury/OMB
# into larger buckets meant to roughly correspond with JCT
# tax break estimates. We do this so we can overlay CBO's
# data on the distributional effects of major tax breaks.

def prep_aggregate(df):
    df['percent_omb_cat'] = np.nan
    df['percent_npp_cat'] = np.nan
    df['omb_cat'] = ' '
    df['npp_cat'] = ' '
    df.corp_adj = df.corp_adj.astype(np.float)
    df.indv_adj = df.indv_adj.astype(np.float)
    df.total_adj = df.total_adj.astype(np.float)
    df = df.groupby(['npp_cat', 'omb_cat', 'name', 'year', 'gdp', 'gdp_price_index']).sum().reset_index()
    return df

def percent_change_agg(row):
    try:
        last_year = agg[(agg.year == row['year']-1) & 
            (agg.name == row['name'])].reset_index()['total_adj'][0]
        if last_year == 0:
            return np.nan
        else:
            return (row['total_adj'] - last_year) / last_year * 100
    except:
        return np.nan

def add_percentage_columns(df):
    df = df.merge(df.apply(lambda row: pd.Series({
        'percent_total':row['total']/year_total[row['year']]*100,
        'percent_corp':row['corp']/corp_total[row['year']]*100,
        'percent_indv':row['indv']/indv_total[row['year']]*100,
        'percent_gdp':row['total']/row['gdp']*100,
        }),axis=1),left_index=True, right_index=True)
    return df

def round_agg(df):
    df['corp_adj'],df['indv_adj'],df['total_adj'] = (
    df['corp_adj'].map(lambda x: round_dollar(x)),
    df['indv_adj'].map(lambda x: round_dollar(x)),
    df['total_adj'].map(lambda x: round_dollar(x))
    )
    df['percent_corp'], df['percent_gdp'], df['percent_indv'], df['percent_npp_cat'], df['percent_omb_cat'], df['percent_total'], df['percent_change'] = (
        df['percent_corp'].map(lambda x: round_percent(x)),
        df['percent_gdp'].map(lambda x: round_percent(x)),
        df['percent_indv'].map(lambda x: round_percent(x)),
        df['percent_npp_cat'].map(lambda x: round_percent(x)),
        df['percent_omb_cat'].map(lambda x: round_percent(x)),
        df['percent_total'].map(lambda x: round_percent(x)),
        df['percent_change'].map(lambda x: round_percent(x))
    )
    return df

te_agg = te

#capital gains
include_pattern = '(Capital Gains)'
capgains = te_agg[te_agg['name'].str.contains(include_pattern)]
exclude_death = '^((?!Death).)*$'
capgains = capgains[capgains['name'].str.contains(exclude_death)]
exclude_home = '^((?!Home).)*$'
capgains = capgains[capgains['name'].str.contains(exclude_home)]
exclude_gift = '^((?!Gift).)*$'
capgains = capgains[capgains['name'].str.contains(exclude_gift)]
dividends = te_agg[te_agg['name'].str.contains('Treatment Of Qualified Dividends')]
agg = pd.concat([capgains, dividends])
te_agg = te_agg.drop(agg.index)
agg['name'] = 'Special Rate on Capital Gains and Dividends'
agg = prep_aggregate(agg)
agg = add_percentage_columns(agg)
agg['percent_change'] = agg.apply(lambda row: percent_change_agg(row), axis=1)
agg = round_agg(agg)
viz = agg

#capital gains - home sales
home_sales = te_agg[te_agg['name'].str.contains('Home Sales')]
agg = home_sales
te_agg = te_agg.drop(agg.index)
agg['name'] = 'Exclusion of Capital Gains on Home Sales'
agg = prep_aggregate(agg)
agg = add_percentage_columns(agg)
agg['percent_change'] = agg.apply(lambda row: percent_change_agg(row), axis=1)
agg = round_agg(agg)
viz = pd.concat([viz, agg])

#social security & railroad retirement benefits
ss = te_agg[te_agg['name'].str.contains('Social Security Benefits For Retired Workers')]
rr = te_agg[te_agg['name'].str.contains('Exclusion Of Railroad Retirement System Benefits')]
agg = pd.concat([ss, rr])
te_agg = te_agg.drop(agg.index)
agg['name'] = 'Exclusion of Social Security and Railroad System Retirement Benefits'
agg = prep_aggregate(agg)
agg = add_percentage_columns(agg)
agg['percent_change'] = agg.apply(lambda row: percent_change_agg(row), axis=1)
agg = round_agg(agg)
viz = pd.concat([viz, agg])

#charitable contributions
agg = te_agg[te_agg['name'].str.contains('Charitable Contributions')]
te_agg = te_agg.drop(agg.index)
agg['name'] = 'Deduction of Charitable Contributions'
agg = prep_aggregate(agg)
agg = add_percentage_columns(agg)
agg['percent_change'] = agg.apply(lambda row: percent_change_agg(row), axis=1)
agg = round_agg(agg)
viz = pd.concat([viz, agg])

#net pension contributions and earnings
employer_plans = te_agg[te_agg['name'].str.contains('Employer Plans')]
pattern_401k = '(401\(K\))'
k401 = te_agg[te_agg['name'].str.contains(pattern_401k)]
keogh = te_agg[te_agg['name'].str.contains('Keogh')]
agg = pd.concat([employer_plans, k401, keogh])
te_agg = te_agg.drop(agg.index)
agg['name'] = 'Exclusion of Employer-Sponsored Retirement Plans'
agg = prep_aggregate(agg)
agg = add_percentage_columns(agg)
agg['percent_change'] = agg.apply(lambda row: percent_change_agg(row), axis=1)
agg = round_agg(agg)
viz = pd.concat([viz, agg])

viz = pd.concat([te_agg, viz], ignore_index=True)

#spiff up some tax break names for display
viz['name'] = viz['name'].str.replace('Exclusion Of Employer Contributions For Medical Insurance Premiums And Medical Care',
    'Exclusion of Employer-Sponsored Health Care')
viz['name'] = viz['name'].str.replace('Deductibility Of Mortgage Interest On Owner-Occupied Homes',
    'Deduction of Home Mortgage Interest')
viz['name'] = viz['name'].str.replace('Exclusion Of Net Imputed Rental Income',
    'Exclusion of Imputed Rental Income')
viz['name'] = viz['name'].str.replace('Deductibility Of Nonbusiness State And Local Taxes Other Than On Owner-Occupied Homes',
    'Deduction of State and Local Taxes')
viz['name'] = viz['name'].str.replace('Deferral Of Income From Controlled Foreign Corporations',
    'Deferral of Corporate Income Earned Abroad')
viz['name'] = viz['name'].str.replace('Deductibility Of Charitable Contributions, Other Than Education And Health',
    'Deduction of Charitable Contributions (Other Than Education and Health)')
viz['name'] = viz['name'].str.replace('Exclusion Of Interest On Public Purpose State And Local Bonds',
    'Exclusion of Interest Income on State and Local Bonds')

viz.sort(['year','name'], inplace=True)
viz.to_csv('%s' % TAX_BREAK_COMPLETE_CBO, index=False,
    cols = ['omb_cat','name','year', 'corp', 'indv', 'total', 'gdp', 'gdp_price_index', 
    'corp_adj', 'indv_adj', 'total_adj', 'percent_corp', 'percent_gdp',
    'percent_indv', 'percent_omb_cat', 'percent_total', 'percent_change'])
