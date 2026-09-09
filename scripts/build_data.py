import os, json, shutil, re
import pandas as pd
import geopandas as gpd
from collections import defaultdict

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA=os.path.join(ROOT,'source','Dhaka_2022_Census_MapData.csv')
GPKG=os.path.join(ROOT,'source','Dhaka_2022_Census_MapGeometry_final.gpkg')
XLSX=os.path.join(ROOT,'source','Dhaka_2022_census_data.xlsx')

# Copy authoritative source files
os.makedirs(f'{ROOT}/source', exist_ok=True)

csv=pd.read_csv(DATA, low_memory=False)
g=gpd.read_file(GPKG, layer='map_units')

# Indicator definitions. Labels are taken from the original Excel table headers.
def F(field,label,typ='number'):
    return {'field':field,'label':label,'type':typ}
def G(title, fields): return {'title':title,'fields':fields}
def T(code,title,groups): return {'code':code,'title':title,'groups':groups}

IND=[
T('C-01','Household, Population and Sex Ratio',[
 G('Household (Except Floating Household)',[
  F('c_01_household_except_floating_household_total','Total'),F('c_01_general','General'),F('c_01_institutional','Institutional'),F('c_01_others','Others')]),
 G('Population (Including Floating Population)',[
  F('c_01_population_including_floating_population_total','Total'),F('c_01_male','Male'),F('c_01_female','Female'),F('c_01_hijra','Hijra')]),
 G('Sex Ratio',[F('c_01_sex_ratio','Sex Ratio','decimal')])]),
T('C-02','Population by Age Group',[
 G('Population',[F('c_02_total','Total')]),
 G('Age Group (in years)',[F('c_02_age_group_in_years_0_4','0-4'),F('c_02_5_9','5-9'),F('c_02_10_14','10-14'),F('c_02_15_19','15-19'),F('c_02_20_24','20-24'),F('c_02_25_29','25-29'),F('c_02_30_34','30-34'),F('c_02_35_39','35-39'),F('c_02_40_44','40-44'),F('c_02_45_49','45-49'),F('c_02_50_54','50-54'),F('c_02_55_59','55-59'),F('c_02_60_64','60-64'),F('c_02_65_69','65-69'),F('c_02_70_74','70-74'),F('c_02_75_79','75-79'),F('c_02_80','80+')])]),
T('C-03','Population by Religion',[
 G('Population',[F('c_03_total','Total'),F('c_03_muslim','Muslim'),F('c_03_hindu','Hindu'),F('c_03_christian','Christian'),F('c_03_buddhist','Buddhist'),F('c_03_others','Others')])]),
T('C-04','Marital Status of Population Aged 10 Years and above by Sex',[
 G('Male',[F('c_04_male_population_number','Population (Number)'),F('c_04_total','Total'),F('c_04_never_married','Never Married'),F('c_04_currently_married','Currently Married'),F('c_04_widowed_widower','Widowed/ Widower'),F('c_04_divorced','Divorced'),F('c_04_separated','Separated')]),
 G('Female',[F('c_04_female_population_number','Population (Number)'),F('c_04_total_2','Total'),F('c_04_never_married_2','Never Married'),F('c_04_currently_married_2','Currently Married'),F('c_04_widowed_widower_2','Widowed/ Widower'),F('c_04_divorced_2','Divorced'),F('c_04_separated_2','Separated')])]),
T('C-05','Literacy Rate by Sex',[
 G('5 Years and above',[F('c_05_5_years_and_above_total','Total','percent'),F('c_05_male','Male','percent'),F('c_05_female','Female','percent')]),
 G('7 Years and above',[F('c_05_7_years_and_above_total','Total','percent'),F('c_05_male_2','Male','percent'),F('c_05_female_2','Female','percent')]),
 G('15 Years and above',[F('c_05_15_years_and_above_total','Total','percent'),F('c_05_male_3','Male','percent'),F('c_05_female_3','Female','percent')])]),
T('C-06','Population Aged 5 Years and above by Field of Education and Highest Level of Education Attained',[
 G('Population (Number)',[F('c_06_population_number','Population (Number)')]),
 G('Field of Education',[F('c_06_field_of_education_total','Total'),F('c_06_general','General'),F('c_06_technical','Technical'),F('c_06_religious','Religious'),F('c_06_others','Others')]),
 G('Highest Level of Education Attained',[F('c_06_highest_level_of_education_attained_total','Total'),F('c_06_attended_school_but_not_completed_play_nursery_kg_pre_primary_class_i','Attended School but Not Completed Play/Nursery/ KG/Pre-Primary/Class I'),F('c_06_play_nursery_kg_pre_primary_student','Play/Nursery/KG/Pre-Primary student'),F('c_06_student_class_i','Student-Class I'),F('c_06_class_i_v','Class I- V'),F('c_06_class_vi_ix','Class VI- IX'),F('c_06_ssc_dakhil_o_level_equivalent','SSC/Dakhil/O-Level/Equivalent'),F('c_06_hsc_alim_a_level_equivalent','HSC/Alim/A-Level/Equivalent'),F('c_06_diploma_nursing_midwifery','Diploma/Nursing/Midwifery'),F('c_06_graduate_and_above','Graduate and above*'),F('c_06_non_formal_informal_education_and_others','Non-formal/Informal Education and Others')])]),
T('C-07','Currently Student Aged 5-29 Years by Sex',[
 G('Total',[F('c_07_total_male','Male'),F('c_07_female','Female')]),
 G('5-9 Years',[F('c_07_5_9_years_male','Male'),F('c_07_female_2','Female')]),
 G('10-14 Years',[F('c_07_10_14_years_male','Male'),F('c_07_female_3','Female')]),
 G('15-19 Years',[F('c_07_15_19_years_male','Male'),F('c_07_female_4','Female')]),
 G('20-24 Years',[F('c_07_20_24_years_male','Male'),F('c_07_female_5','Female')]),
 G('25-29 Years',[F('c_07_25_29_years_male','Male'),F('c_07_female_6','Female')])]),
T('C-08','Population Aged 5 Years and above by Working Status and Sex',[
 G('Population',[F('c_08_population_total','Total'),F('c_08_male','Male'),F('c_08_female','Female')]),
 G('Employed',[F('c_08_employed_total','Total'),F('c_08_male_2','Male'),F('c_08_female_2','Female')]),
 G('Household Work',[F('c_08_household_work_total','Total'),F('c_08_male_3','Male'),F('c_08_female_3','Female')]),
 G('Looking for Work',[F('c_08_looking_for_work_total','Total'),F('c_08_male_4','Male'),F('c_08_female_4','Female')]),
 G('Do not Work',[F('c_08_do_not_work_total','Total'),F('c_08_male_5','Male'),F('c_08_female_5','Female')])]),
T('C-09','Employed Population Aged 5 Years and above by Sector and Sex',[
 G('Total',[F('c_09_total','Total'),F('c_09_male','Male'),F('c_09_female','Female')]),
 G('Agriculture',[F('c_09_agriculture_total','Total'),F('c_09_male_2','Male'),F('c_09_female_2','Female')]),
 G('Industry',[F('c_09_industry_total','Total'),F('c_09_male_3','Male'),F('c_09_female_3','Female')]),
 G('Service',[F('c_09_service_total','Total'),F('c_09_male_4','Male'),F('c_09_female_4','Female')])]),
T('C-10','Population Aged 15-24 Years Not in Education, Employment or Training (NEET)',[
 G('Total',[F('c_10_total','Total','percent'),F('c_10_15_19_years','15-19 Years','percent'),F('c_10_20_24_years','20-24 Years','percent')]),
 G('Male',[F('c_10_male_total','Total','percent'),F('c_10_15_19_years_2','15-19 Years','percent'),F('c_10_20_24_years_2','20-24 Years','percent')]),
 G('Female',[F('c_10_female_total','Total','percent'),F('c_10_15_19_years_3','15-19 Years','percent'),F('c_10_20_24_years_3','20-24 Years','percent')])]),
T('C-11','Population having Mobile Phone for Own Use and Internet User',[
 G('Population having Mobile Phone for Own Use — 5 Years and above',[F('c_11_5_years_and_above_total','Total','percent'),F('c_11_male','Male','percent'),F('c_11_female','Female','percent')]),
 G('Population having Mobile Phone for Own Use — 15 Years and above',[F('c_11_15_years_and_above_total','Total','percent'),F('c_11_male_2','Male','percent'),F('c_11_female_2','Female','percent')]),
 G('Internet User — 5 Years and above',[F('c_11_5_years_and_above_total_2','Total','percent'),F('c_11_male_3','Male','percent'),F('c_11_female_3','Female','percent')]),
 G('Internet User — 15 Years and above',[F('c_11_15_years_and_above_total_2','Total','percent'),F('c_11_male_4','Male','percent'),F('c_11_female_4','Female','percent')])]),
T('C-12','Population Aged 15 Years and above having Account in Financial Institution and Mobile Banking Account',[
 G('Having Account in Financial Institution (Bank/Insurance/Micro-credit/Post office etc.)',[F('c_12_having_account_in_financial_institution_bank_insurance_micro_credit_post_office_etc_total','Total','percent'),F('c_12_male','Male','percent'),F('c_12_female','Female','percent')]),
 G('Having Mobile Banking Account',[F('c_12_having_mobile_banking_account_total','Total','percent'),F('c_12_male_2','Male','percent'),F('c_12_female_2','Female','percent')])]),
T('C-13','Ethnic Population by Major Ethnic Group and Sex',[
 G('Ethnic Population',[F('c_13_ethnic_population_total','Total'),F('c_13_male','Male'),F('c_13_female','Female')]),
 G('Ethnic Population in Major Groups',[F('c_13_ethnic_population_in_major_groups_garo','Garo'),F('c_13_chakma','Chakma'),F('c_13_marma','Marma'),F('c_13_others','Others')])]),
T('C-14','General Household by Structure of Main Dwelling Unit and Ownership Status',[
 G('General Household',[F('c_14_general_household','General Household')]),
 G('Type of Structure',[F('c_14_type_of_structure_total','Total','percent'),F('c_14_pucca','Pucca','percent'),F('c_14_semi_pucca','Semi-pucca','percent'),F('c_14_kancha','Kancha','percent'),F('c_14_jhupri','Jhupri','percent')]),
 G('Ownership Status',[F('c_14_ownership_status_total','Total','percent'),F('c_14_own_dwelling_unit','Own dwelling unit','percent'),F('c_14_rented_but_having_own_dwelling_unit_elsewhere','Rented but having own dwelling unit elsewhere','percent'),F('c_14_rented_and_having_no_own_dwelling_unit_elsewhere','Rented and having no own dwelling unit elsewhere','percent'),F('c_14_rent_free_but_having_own_dwelling_unit_elsewhere','Rent free but having own dwelling unit elsewhere','percent'),F('c_14_rent_free_and_having_no_own_dwelling_unit_elsewhere','Rent free and having no own dwelling unit elsewhere','percent')])]),
T('C-15','General Household by Main Source of Drinking Water',[
 G('General Household',[F('c_15_general_household','General Household')]),
 G('Source of Drinking Water',[F('c_15_source_of_drinking_water_total','Total','percent'),F('c_15_tap_pipe_supply','Tap/pipe (Supply)','percent'),F('c_15_tube_well_deep_shallow','Tube-well (Deep/Shallow)','percent'),F('c_15_bottled_jar_water','Bottled/Jar Water','percent'),F('c_15_well','Well','percent'),F('c_15_pond_river_canal_lake','Pond/River/ Canal/lake','percent'),F('c_15_spring','Spring','percent'),F('c_15_rain_water','Rain Water','percent'),F('c_15_others','Others','percent')])]),
T('C-16','General Household by Toilet Facilities',[
 G('General Household',[F('c_16_general_household','General Household')]),
 G('Toilet Facilities',[F('c_16_toilet_facilities_total','Total','percent'),F('c_16_safe_disposal_with_flushing_pouring_water','Safe Disposal with Flushing/ Pouring Water','percent'),F('c_16_unsafe_disposal_with_flushing_pouring_water','Unsafe Disposal with Flushing/ Pouring Water','percent'),F('c_16_pit_latrine_with_slab_ventilated_improved_latrine_composting_latrine','Pit Latrine with Slab/ Ventilated Improved Latrine/ Composting Latrine','percent'),F('c_16_pit_latrine_without_slab_open_pit','Pit Latrine without Slab/ Open Pit','percent'),F('c_16_raw_open_hanging_latrine_permanent_temporary','Raw/Open/ Hanging Latrine (Permanent/ Temporary)','percent'),F('c_16_open_defecation_no_latrine_available','Open Defecation/ No Latrine Available','percent')])]),
T('C-17','General Household by Main Source of Cooking Fuel and Electricity Coverage',[
 G('General Household',[F('c_17_general_household','General Household')]),
 G('Source of Cooking Fuel',[F('c_17_source_of_cooking_fuel_total','Total','percent'),F('c_17_straw_leaf_bran_husk','Straw/ Leaf/ Bran/ Husk','percent'),F('c_17_wood_chalk_chopped_wood','Wood/ Chalk/ Chopped Wood','percent'),F('c_17_wood_coal_charcoal_dried_dung','Wood-coal/ Charcoal/ Dried Dung','percent'),F('c_17_kerosene_paraffin','Kerosene/ Paraffin','percent'),F('c_17_petrol_diesel','Petrol/ Diesel','percent'),F('c_17_electricity','Electricity','percent'),F('c_17_supply_gas','Supply Gas','percent'),F('c_17_lp_gas','LP Gas','percent'),F('c_17_biogas','Biogas','percent'),F('c_17_others','Others','percent')]),
 G('Electricity Coverage',[F('c_17_electricity_coverage','Electricity Coverage','percent')])]),
T('C-18','Comprising of General Household by Number of Persons and Average Household Size',[
 G('General Household',[F('c_18_general_household','General Household')]),
 G('Household Comprising',[F('c_18_household_comprising_1_person','1 Person'),F('c_18_2_person','2 Person'),F('c_18_3_person','3 Person'),F('c_18_4_person','4 Person'),F('c_18_5_person','5 Person'),F('c_18_6_person','6 Person'),F('c_18_7_person','7 Person'),F('c_18_8_person','8 Person'),F('c_18_9_person','9 Person'),F('c_18_10_person','10 Person'),F('c_18_10_person_2','10 Person+')]),
 G('Average Household Size',[F('c_18_average_household_size','Average Household Size','decimal')])]),
]

# SDG definitions (last two source columns are location/code metadata, not indicators)
IND.append(T('SDG','SDG Indicators by Union',[
 G('Participation in Organized Learning (4.2.2)',[F('sdg_indicator_by_union_participation_in_organized_learning_4_2_2_total','Total','percent'),F('sdg_indicator_by_union_male','Male','percent'),F('sdg_indicator_by_union_female','Female','percent')]),
 G('Ownership of mobile phone (5.b.1)',[F('sdg_indicator_by_union_ownership_of_mobile_phone_5_b_1_total','Total','percent'),F('sdg_indicator_by_union_male_2','Male','percent'),F('sdg_indicator_by_union_female_2','Female','percent')]),
 G('Basic Sanitation Service (6.2.1 (a))',[F('sdg_indicator_by_union_basic_sanitation_service_6_2_1_a','Value','percent')]),
 G('Basic Handwashing Facilities (6.2.1 (b))',[F('sdg_indicator_by_union_basic_handwashing_facilities_6_2_1_b','Value','percent')]),
 G('Access to Electricity (7.1.1)',[F('sdg_indicator_by_union_access_to_electricity_7_1_1','Value','percent')]),
 G('Clean Fuel (7.1.2)',[F('sdg_indicator_by_union_clean_fuel_7_1_2','Value','percent')]),
 G('NEET Youth Population (8.6.1)',[F('sdg_indicator_by_union_neet_youth_population_8_6_1_total','Total','percent'),F('sdg_indicator_by_union_male_3','Male','percent'),F('sdg_indicator_by_union_female_3','Female','percent')]),
 G('Financial Inclusion (8.10.2)',[F('sdg_indicator_by_union_financial_inclusion_8_10_2_total','Total','percent'),F('sdg_indicator_by_union_male_4','Male','percent'),F('sdg_indicator_by_union_female_4','Female','percent')]),
 G('Urban Slum (11.1.1)',[F('sdg_indicator_by_union_urban_slum_11_1_1_total','Total','percent'),F('sdg_indicator_by_union_male_5','Male','percent'),F('sdg_indicator_by_union_female_5','Female','percent')]),
 G('Internet User (17.8.1)',[F('sdg_indicator_by_union_internet_user_17_8_1_total','Total','percent'),F('sdg_indicator_by_union_male_6','Male','percent'),F('sdg_indicator_by_union_female_6','Female','percent')])]))

# Validate all fields exist
all_fields=[f['field'] for t in IND for gr in t['groups'] for f in gr['fields']]
missing=[f for f in all_fields if f not in csv.columns]
if missing: raise SystemExit('Missing fields: '+repr(missing))

# Add display name lookup
label_lookup={f['field']:f['label'] for t in IND for gr in t['groups'] for f in gr['fields']}
type_lookup={f['field']:f['type'] for t in IND for gr in t['groups'] for f in gr['fields']}

# Clean numeric values and create compact per-admin-type JSON. Only indicator values are sent to browser.
# Keep all census rows; city_thana is support data, not a clickable navigation level.
admin_types=['district','city_corporation','upazila','city_ward','paurashava','paurashava_ward','union','mauza','village','city_thana']
os.makedirs(f'{ROOT}/public/data/census',exist_ok=True)
for at in admin_types:
    sub=csv[csv['matched_key'].isin(set(g.loc[g.admin_type==at,'matched_key']))].copy()
    rows=[]
    for _,r in sub.iterrows():
        vals={}
        for field in all_fields:
            v=r.get(field)
            if pd.isna(v):
                continue
            if isinstance(v,str):
                vv=v.strip()
                if vv in ('','-','—'): continue
                try:
                    # Keep numeric strings numeric
                    num=float(vv)
                    v=int(num) if num.is_integer() else num
                except Exception: v=vv
            elif hasattr(v,'item'):
                v=v.item()
            vals[field]=v
        rows.append({'id':r['matched_key'],'values':vals})
    with open(f'{ROOT}/public/data/census/{at}.json','w',encoding='utf-8') as f: json.dump(rows,f,ensure_ascii=False,separators=(',',':'))

# Geometry: simplified, original CRS EPSG:4326, properties only needed for navigation.
# Small topology-preserving simplification reduces browser payload substantially.
geom=g.copy()
geom['geometry']=geom.geometry.simplify(0.00005,preserve_topology=True)
props_cols=['matched_key','navigation_parent_key','admin_type','admin_label','map_level','admin_rank','displayable','geometry_status','location_label']
for at in admin_types:
    sub=geom[geom.admin_type==at][props_cols+['geometry']].copy()
    # GeoJSON null geometries are retained for the five genuine missing cases.
    out=f'{ROOT}/public/data/geojson/{at}.geojson'
    sub.to_file(out,driver='GeoJSON')

# Indicator metadata
with open(f'{ROOT}/public/data/indicators.json','w',encoding='utf-8') as f: json.dump(IND,f,ensure_ascii=False,indent=2)

# Initial summary data and README data QA
summary={
 'rows':len(csv),'features':len(g),'geometry_features':int(g.geometry.notna().sum()),
 'missing_geometry':int(g.geometry.isna().sum()),
 'admin_type_counts':g.admin_type.value_counts().to_dict()
}
with open(f'{ROOT}/public/data/summary.json','w') as f: json.dump(summary,f,indent=2)

print('built',ROOT)
print(summary)
print('indicator fields',len(all_fields))
for fn in ['district','city_corporation','upazila','city_ward','paurashava','paurashava_ward','union','mauza','village','city_thana']:
 p=f'{ROOT}/public/data/geojson/{fn}.geojson'; print(fn,os.path.getsize(p)/1e6,'MB')
