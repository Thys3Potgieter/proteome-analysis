import csv
import pandas as pd
from pandas.io.parsers import read_csv
from scipy.stats import gaussian_kde,linregress
from Bio import SeqIO
from matplotlib.pyplot import hist, savefig, figure,figlegend,legend,plot,xlim,ylim,xlabel,ylabel,tight_layout,tick_params,subplot,subplots_adjust
from numpy import linspace,ndarray,arange
from numpy.random import randn

remove_unmapped = False
just_ribosomes = False
use_LB = False
id_col_dict = { 'valgepea':'ko_num', 'heinmann':u'UP_AC' }
db_used = 'valgepea'

conf_fname_mod = '%s%s%s%s' % ('RibsOnly' if just_ribosomes else '', 'AnnotOnly' if remove_unmapped else '',"LB" if use_LB else '',db_used)

#Initialization of basic data containers, gene annotation data, growth rates and cell volumes and selection of conditions to analyze.
def ko_to_desc_dict():
    ko_annot_dict = {}

    with open('hierarchy_standardised.tms','rb') as annot_file:
         annots = csv.reader(annot_file,delimiter='\t') #,encoding='iso-8859-1')
         for row in annots:
             if len(row) == 2:
                cat = row [-1]
             elif len(row) == 3:
                subcat = row[-1]
             elif len(row) == 4:
                component = row[-1]
             elif len(row) == 5:
                ko_annot_dict[row[-1]]=(cat,subcat,component)
    return ko_annot_dict

def uniprot_to_desc_dict():
    uni_konum_dict = {}
    uni_to_konum = read_csv('eco_uniprot_mapping.csv',sep='[\t:]',encoding='iso-8859-1',header = None, names = ['ko','bla','uniprot'])
    for i,row in uni_to_konum.iterrows():
         uni_konum_dict[row['uniprot']]=row['ko']    

    #load the ko annotation tree:
    ko_annot_dict = ko_to_desc_dict()
    uni_to_annot = {}
    for uni in uni_konum_dict:
        if uni_konum_dict[uni] == 'NotMapped':
            uni_to_annot[uni]=['NotMapped']
        elif uni_konum_dict[uni] not in ko_annot_dict:
	    uni_to_annot[uni]=['NotMapped']
        else:
            uni_to_annot[uni]=ko_annot_dict[uni_konum_dict[uni]]
    return uni_to_annot

def uniprot_to_offset():
    #load location information for genes:
    genome = SeqIO.read('U00096.2.gbk','genbank')

    locus_to_offset = {}
    for feat in genome.features:
        if feat.type == 'CDS':
           locus_to_offset[feat.qualifiers['locus_tag'][0]]=feat.location.start.real

    uniprot_to_locus = {}
    for row in open('all_ecoli_genes.txt','r'):
        uniprot_to_locus[row[48:54]]=row[0:5]

    uniprot_to_location = {}
    for uni in uniprot_to_locus.keys():
        if uniprot_to_locus[uni] in locus_to_offset.keys():
            uniprot_to_location[uni]= locus_to_offset[uniprot_to_locus[uni]]
        else:
            uniprot_to_location[uni]= 0
    return uniprot_to_location

# Define the list of conditions that will be relevant for the analysis, (and the description column), the growth rates and the cell volumes, according to the database used:
cond_list_dict = {'valgepea':[u'11', u'21', u'31', u'40', u'48'],
                  'heinmann':[
                      u'chemostat \u00b5=0.12', u'galactose',
                      u'chemostat \u00b5=0.20', u'acetate',
                      u'chemostat \u00b5=0.35', u'glucosamine',
                      u'pyruvate', u'glycerol', u'fumarate',
                      u'succinate', u'chemostat \u00b5=0.5',
                      u'anaerobic', u'glucose',]
                  }
if use_LB:
    cond_list_dict['heinmann'].append(u'LB')

gr_dict = {'valgepea':
    {u'11': 0.11, u'21':0.21, u'31':0.31, u'40':0.4, u'48':0.48},
           'heinmann':
    {u'chemostat \u00b5=0.12': 0.12, u'galactose':0.17, 
     u'chemostat \u00b5=0.20':0.2, u'acetate':0.29, 
     u'chemostat \u00b5=0.35':0.35, u'glucosamine':0.39, 
     u'pyruvate':0.4, u'glycerol':0.47, u'fumarate':0.47, 
     u'succinate':0.49, u'chemostat \u00b5=0.5':0.5, 
     u'anaerobic' : 0.55, u'glucose': 0.6, u'LB':1.61}
           }

def get_coli_data(db_used,use_weight):
    cond_list = cond_list_dict[db_used]
    if db_used == 'heinmann':
        # As the file was exported from Excel, it uses Excel's encoding.
        ecoli_data = read_csv('coli_data.csv',header=1,encoding='iso-8859-1')

        #Split the data loaded into two sets - weight and count.
        idx = ecoli_data.columns
        ecoli_data_count = ecoli_data[idx[0:29]]
        ecoli_data_weight = ecoli_data[idx[0:10].append(idx[29:])]

        # Refine the DataFrames to include only these conditions (and the protein descriptions):
        desc_list = [id_col_dict[db_used]]
        count_cond = desc_list+cond_list
        ecoli_data_count = ecoli_data_count[count_cond]

        #duplicate headers are modified by read_csv and include a trailing '.1' string in their name.
        weight_cond = desc_list+[x+'.1' for x in cond_list] 
        ecoli_data_weight = ecoli_data_weight[weight_cond]

        #rename the columns to remove the trailing '.1'
        ecoli_data_weight.columns = count_cond

        #select the relevant data for analysis out of the two options:
        if use_weight:
            ecoli_data = ecoli_data_weight
        else:
            ecoli_data = ecoli_data_count

        #convert all data columns to floats, and description columns to strings.
        ecoli_data = ecoli_data[ecoli_data != 'below LOQ']
        ecoli_data[cond_list] = ecoli_data[cond_list].astype('float')

    if db_used == 'valgepea':
        ecoli_data = read_csv('valgepea.csv',header=0,encoding='iso-8859-1')

    #Normalize to get concentrations 
    ecoli_data[cond_list] = ecoli_data[cond_list] / ecoli_data[cond_list].sum()
    id_col = id_col_dict[db_used]
    ecoli_data[id_col] = ecoli_data[id_col].astype('string')
    return ecoli_data

def get_annotated_prots(db):
    coli_data = get_coli_data(db,use_weight=True)
    #annotate coli_data according to db.
    id_col = id_col_dict[db]
    if db == 'heinmann':
        id_to_annot = uniprot_to_desc_dict()
    if db == 'valgepea':
        id_to_annot = ko_to_desc_dict()
    coli_data['group']=coli_data.apply(lambda x: 'NotMapped' if x[id_col] not in id_to_annot else (id_to_annot[x[id_col]])[0],axis=1)
    coli_data['func']=coli_data.apply(lambda x: 'NotMapped' if (x[id_col] not in id_to_annot) or (len(id_to_annot[x[id_col]]) < 3) else (id_to_annot[x[id_col]])[2],axis=1)

    if just_ribosomes:
        coli_data = coli_data[coli_data['func']=='Ribosome']
    if remove_unmapped:
        coli_data = coli_data[coli_data['group'] != 'NotMapped']

    coli_data = coli_data.dropna()
    gr = gr_dict[db]
    gr = pd.Series(gr)
    cond_list = cond_list_dict[db]
    gr = gr[cond_list]
    return (cond_list,gr,coli_data)

def calc_gr_corr(df,cond_list,gr):
    df['gr_cov']=df[cond_list].apply(lambda x: x.corr(gr[cond_list]),axis=1)
    df['rsq']=df['gr_cov']**2
    return df

def add_loc_info(df):
    if db_used == 'heinmann':
        uni_to_loc = uniprot_to_offset()
        conc_data['loc']=conc_data.apply(lambda x: 0 if x[id_col_dict[db_used]] not in uni_to_loc else uni_to_loc[x[id_col_dict[db_used]]],axis=1)


### Results generation#####
### Figure 1 - Correlation to growth rate by functional group histogram.
(cond_list_v,gr_v,ecoli_data_v) = get_annotated_prots('valgepea')
(cond_list_h,gr_h,ecoli_data_h) = get_annotated_prots('heinmann')
ecoli_data_h = calc_gr_corr(ecoli_data_h,cond_list_h,gr_h)
ecoli_data_v = calc_gr_corr(ecoli_data_v,cond_list_v,gr_v)

categories = set(ecoli_data_v['group'].values).union(set(ecoli_data_h['group'].values))

# Remove the unmapped proteins first and add them at the end so that they are stacked last in the histogram.
if not remove_unmapped and "NotMapped" in categories:
    categories.remove("NotMapped")
categories = list(categories)

if not just_ribosomes:
    categories.append('NotMapped')

figure(figsize=(5,3))

p=subplot(111)
p1=subplot(121)
p2=subplot(122)

def plot_corr_hist(p,conc_data,categories):
    bins = linspace(-1,1,20)
    covs = ndarray(shape=(len(categories),len(bins)-1))
    sets = [] 

    for x in categories:
        sets.append(conc_data[conc_data['group']==x].gr_cov)

    p.hist(sets,bins = bins, stacked = True,label=categories)
    handles,labels=p.get_legend_handles_labels()
    p.tick_params(axis='both', which='major', labelsize=8)
    p.tick_params(axis='both', which='minor', labelsize=8)
    p.set_xlabel('Pearson correlation with growth rate',fontsize=8)
    p.set_ylabel('Number of proteins',fontsize=8)

    #legend(loc=2,prop={'size':8})
    tight_layout()
    return handles,labels

plot_corr_hist(p1,ecoli_data_h,categories)
plot_corr_hist(p2,ecoli_data_v,categories)

#assume both subplots have the same categories.
handles,labels=p1.get_legend_handles_labels()

figlegend(handles,labels,fontsize=6,mode='expand',loc='upper left',bbox_to_anchor=(0.2,0.8,0.6,0.2),ncol=2)
subplots_adjust(top=0.83)
savefig('GrowthRateCorrelation.pdf')

### Global cluster analysis:
## The proteins that show a high correlation with growth rate have significant R^2 values.
## They change by xx fold across conditions measured.
## The correlation of each of the proteins with the global cluster is higher than with the GR (meaning it compensates for errors in GR measurements or degredation rates).
figure(figsize=(5,3))

def get_glob(db,df):
    if db == 'heinmann' and not use_LB:
        limits = (0.4,0.8)
    if db == 'heinmann' and use_LB:
        limits = (0.6,1.)
    if db == 'valgepea':
        limits = (0.8,1.)
    glob = df[df['gr_cov']>limits[0]]
    glob = glob[glob['gr_cov']<limits[1]]
    return glob
 
def get_high_corr(db,df,gr,conds):
    glob = get_glob(db,df)
    glob_tot = glob[conds].sum()
    alpha,beta,r_val,p_val,std_err = linregress(gr,glob_tot)
    return (glob_tot,alpha,beta)

(glob_h,alpha_h,beta_h) = get_high_corr('heinmann',ecoli_data_h,gr_h,cond_list_h)
(glob_v,alpha_v,beta_v) = get_high_corr('valgepea',ecoli_data_v,gr_v,cond_list_v)

plot(gr_h.values,glob_h.values,'o',label="Heinmann")
plot(gr_v.values,glob_v.values,'o',label="Valgepea")
plot(gr_h.values,alpha_h*gr_h.values+beta_h,color='blue',label=("Heinmann Trend,$R^2$=%.2f" % (gr_h.corr(glob_h)**2)))
plot(gr_v.values,alpha_v*gr_v.values+beta_v,color='green',label=("Valgepea Trend,$R^2$=%.2f" % (gr_v.corr(glob_v)**2)))

xlim(xmin=0.)
ylim(ymin=0.)
xlabel('Growth rate',fontsize=10)
ylabel('Protein level',fontsize=10)
legend(loc=2, prop={'size':8})
tick_params(axis='both', which='major', labelsize=8)
tick_params(axis='both', which='minor', labelsize=8)
tight_layout()
savefig('GlobalClusterGRFit%s.pdf' % conf_fname_mod)
savefig('GlobalClusterGRFit.pdf')

## Figure 3, global cluster slope vs. ribosomal slope
def set_alpha(db,df,gr):
    cond_list = cond_list_dict[db]
    df['alpha'] = df[cond_list].apply(lambda x: linregress(gr[cond_list]/gr[cond_list].mean(),x/x.mean())[0],axis=1)
    return df

def plot_response_hist(db,df,gr,p):
    bins = linspace(-1.7,1.7,35)
    ribs = df[df['func'] == 'Ribosome']
    glob_conc = get_glob(db,df)
    glob_conc = glob_conc[glob_conc['func'] != 'Ribosome']
    glob_conc = set_alpha(db,glob_conc,gr)
    ribs = set_alpha(db,ribs,gr)
    p.hist([glob_conc['alpha'].values,ribs['alpha'].values],bins=bins,stacked = True,label=['HC-proteins','Ribosomal proteins'])
    p.set_xlim(-1.7,1.7)
    p.set_xlabel('Normalized response')
    p.axvline(x=0,ymin=0,ymax=100)
    p.axvline(x=0.5,ymin=0,ymax=100)
    p.axvline(x=1,ymin=0,ymax=100)
    p.tick_params(axis='both', which='major', labelsize=8)
    p.tick_params(axis='both', which='minor', labelsize=8)

figure(figsize=(6,3))

p1=subplot(121)
p2=subplot(122)
plot_response_hist('valgepea',ecoli_data_v,gr_v,p1)
plot_response_hist('heinmann',ecoli_data_h,gr_h,p2)
tight_layout()
savefig('AllProtsVSRibosomalNormalizedSlopes.pdf')
