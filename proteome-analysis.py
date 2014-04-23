import csv
import pandas as pd
from pandas.io.parsers import read_csv
from scipy.stats import gaussian_kde,linregress
from Bio import SeqIO
from matplotlib.pyplot import hist, savefig, figure,legend,plot,xlim,ylim,xlabel,ylabel,tight_layout,tick_params,subplot
from numpy import linspace,ndarray,arange
from numpy.random import randn

remove_unmapped = False
just_ribosomes = False
use_LB = False
db_used = 'valgepea'
if db_used == 'heinmann':
    id_col=u'UP_AC'
if db_used == 'valgepea':
    id_col='ko_num'

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
if db_used == 'heinmann':
    cond_list = [
        u'chemostat \u00b5=0.12',
        u'galactose',
        u'chemostat \u00b5=0.20',
        u'acetate',
        u'chemostat \u00b5=0.35',
        u'glucosamine',
        u'pyruvate',
        u'glycerol',
        u'fumarate',
        u'succinate',
        u'chemostat \u00b5=0.5',
        u'anaerobic',
        u'glucose',
    ]
    if use_LB:
        cond_list.append(u'LB')

    # define the growth rates:
    gr = {
        u'chemostat \u00b5=0.12': 0.12, 
        u'galactose':0.17, 
        u'chemostat \u00b5=0.20':0.2, 
        u'acetate':0.29, 
        u'chemostat \u00b5=0.35':0.35,
        u'glucosamine':0.39, 
        u'pyruvate':0.4, 
        u'glycerol':0.47,
        u'fumarate':0.47, 
        u'succinate':0.49, 
        u'chemostat \u00b5=0.5':0.5, 
        u'anaerobic' : 0.55, 
        u'glucose': 0.6,
        u'LB':1.61
    }
    gr = pd.Series(gr)
    gr = gr[cond_list]

    # define cell volumes:
    volumes = {
        u'chemostat \u00b5=0.12': 2.1,
        u'galactose':1.9,
        u'chemostat \u00b5=0.20':2.2,
        u'acetate':2.4,
        u'chemostat \u00b5=0.35':2.4,
        u'glucosamine':2.9,
        u'pyruvate':2.1,
        u'glycerol':2.3,
        u'fumarate':2.4,
        u'succinate':2.4,
        u'chemostat \u00b5=0.5':2.6,
        u'anaerobic' : 2.9,
        u'glucose': 3.2,
        u'LB':4.4
    }
    volumes = pd.Series(volumes)
    volumes = volumes[cond_list]

    #Define the text fields that will be relevant for the analysis:
    desc_list = ['Description','UP_AC']
if db_used == 'valgepea':
    cond_list = [
        u'11',
        u'21',
        u'31',
        u'40',
        u'48'
    ]

    # define the growth rates:
    gr = {
        u'11': 0.11, 
        u'21':0.21, 
        u'31':0.31,
        u'40':0.4, 
        u'48':0.48 
    }
    gr = pd.Series(gr)
    gr = gr[cond_list]

    #Define the text fields that will be relevant for the analysis:
    desc_list = ['ko_num']

#Convert dataframe types to standart types for analysis
def convert_types(df):
    df = df[df != 'below LOQ']
    df[cond_list] = df[cond_list].astype('float')
    df[desc_list] = df[desc_list].astype('string')
    return df

def get_coli_data(use_weight):
    if db_used == 'heinmann':
        # As the file was exported from Excel, it uses Excel's encoding.
        ecoli_data = read_csv('coli_data.csv',header=1,encoding='iso-8859-1')

        #Split the data loaded into two sets - weight and count.
        idx = ecoli_data.columns
        ecoli_data_count = ecoli_data[idx[0:29]]
        ecoli_data_weight = ecoli_data[idx[0:10].append(idx[29:])]

        # Refine the DataFrames to include only these conditions (and the protein descriptions):
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
        ecoli_data_weight = convert_types(ecoli_data_weight)
        ecoli_data = convert_types(ecoli_data)

        #Normalize to get concentrations (Use the total protein weight as the normalizing factor to avoid errors in cell volume measurements)
        ecoli_data[cond_list] = ecoli_data[cond_list] / ecoli_data_weight[cond_list].sum() #volumes[cond_list]
        return ecoli_data
    if db_used == 'valgepea':
        ecoli_data = read_csv('valgepea.csv',header=0,encoding='iso-8859-1')
        print ecoli_data
        ecoli_data[cond_list] = ecoli_data[cond_list] / ecoli_data[cond_list].sum()
    return ecoli_data

### Results generation#####
### Figure 1 - Correlation to growth rate by functional group histogram.
uni_to_annot = uniprot_to_desc_dict()
uni_to_loc = uniprot_to_offset()
ko_to_annot = ko_to_desc_dict()
ecoli_data = get_coli_data(use_weight=True)
if db_used == 'heinmann':
    id_to_annot = uni_to_annot
if db_used == 'valgepea':
    id_to_annot = ko_to_annot
conc_data = ecoli_data
conc_data = conc_data.dropna()
conc_data['gr_cov']=conc_data[cond_list].apply(lambda x: x.corr(gr[cond_list]),axis=1)
conc_data['rsq']=conc_data['gr_cov']**2
conc_data['group']=conc_data.apply(lambda x: 'unknown' if x[id_col] not in id_to_annot else (id_to_annot[x[id_col]])[0],axis=1)
conc_data['func']=conc_data.apply(lambda x: '' if (x[id_col] not in id_to_annot) or (len(id_to_annot[x[id_col]]) < 3) else (id_to_annot[x[id_col]])[2],axis=1)
if db_used == 'heinmann':
    conc_data['loc']=conc_data.apply(lambda x: 0 if x[id_col] not in uni_to_loc else uni_to_loc[x[id_col]],axis=1)

if just_ribosomes:
    conc_data = conc_data[conc_data['func']=='Ribosome']

if remove_unmapped:
    conc_data = conc_data[conc_data['group'] != 'NotMapped']

categories = set(conc_data['group'].values)
# Remove the unmapped proteins first and add them at the end so that they are stacked last in the histogram.
if not remove_unmapped and "NotMapped" in categories:
    categories.remove("NotMapped")
bins = linspace(-1,1,20)
covs = ndarray(shape=(len(categories),len(bins)-1))
sets = [] 
figure(figsize=(5,3))
for x in categories:
    sets.append(conc_data[conc_data['group']==x].gr_cov)

if not remove_unmapped and not just_ribosomes:
    sets.append(conc_data[conc_data['group']=="NotMapped"].gr_cov)

cats = list(categories)
cats.append("NotMapped")

hist(sets,bins = bins, stacked = True,label=cats)

tick_params(axis='both', which='major', labelsize=8)
tick_params(axis='both', which='minor', labelsize=8)
xlabel('Pearson correlation with growth rate',fontsize=10)
ylabel('Number of proteins',fontsize=10)

legend(loc=2,prop={'size':8})
tight_layout()
savefig('GrowthRateCorrelation%s.pdf' % conf_fname_mod)
savefig('GrowthRateCorrelation.pdf')


### Global cluster analysis:
## The proteins that show a high correlation with growth rate have significant R^2 values.
## They change by xx fold across conditions measured.
## The correlation of each of the proteins with the global cluster is higher than with the GR (meaning it compensates for errors in GR measurements or degredation rates).
figure(figsize=(5,3))

if db_used == 'heinmann':
    if not use_LB:
        high_corr_prots = conc_data[conc_data['gr_cov']>0.4]
        high_corr_prots = high_corr_prots[high_corr_prots['gr_cov']<0.8]
    if use_LB:
        high_corr_prots = conc_data[conc_data['gr_cov']>0.6]
        high_corr_prots = high_corr_prots[high_corr_prots['gr_cov']<1]
if db_used == 'valgepea':
    high_corr_prots = conc_data[conc_data['gr_cov']>0.8]

high_corr_normed = high_corr_prots.copy()
high_corr_normed = high_corr_normed[cond_list].apply(lambda x: x/x.mean(),axis=1)

def cluster_corr(cluster):
    cluster_global = cluster.sum()
    cluster_global = cluster_global/cluster_global.mean()

    alpha,beta,r_val,p_val,std_err = linregress(gr,cluster_global)
    return (cluster_global,alpha,beta)

global_cluster = {}
global_weighted=cluster_corr(high_corr_prots[cond_list])
global_normed=cluster_corr(high_corr_normed[cond_list])

plot(gr.values,global_weighted[0].values,'o',label="Weighted")
plot(gr.values,global_weighted[1]*gr.values+global_weighted[2],color='blue',label=("Weighted Trend,$R^2$=%f" % (gr.corr(global_weighted[0])**2)))

plot(gr.values,global_normed[0].values,'o',label="Normalized")
plot(gr.values,global_normed[1]*gr.values+global_normed[2],color='green',label=("Normalized Trend,$R^2$=%f" % (gr.corr(global_normed[0])**2)))

if use_LB:
    xlim(0,1.7)
    ylim(0,3)
if not use_LB:
    xlim(0,0.7)
    ylim(0,2)
xlabel('Growth rate',fontsize=10)
ylabel('Protein level (normalized)',fontsize=10)
legend(loc=2, prop={'size':8})
tick_params(axis='both', which='major', labelsize=8)
tick_params(axis='both', which='minor', labelsize=8)
tight_layout()
savefig('GlobalClusterGRFit%s.pdf' % conf_fname_mod)
savefig('GlobalClusterGRFit.pdf')

## Figure 2, correlation inside global cluster
figure(figsize=(5,3))

high_corr_prots['weighted_cov']=high_corr_prots[cond_list].apply(lambda x: x.corr(global_weighted[0]),axis=1)
high_corr_prots['normed_cov']=high_corr_prots[cond_list].apply(lambda x: x.corr(global_normed[0]),axis=1)
sets = [high_corr_prots['weighted_cov'].values,high_corr_prots['normed_cov'].values]
hist(sets,bins = bins, stacked = False,label=['Weighted','Normalized'])
legend(loc=2, prop={'size':8})
xlabel('Pearson correlation with global cluster',fontsize=10)
ylabel('Number of proteins',fontsize=10)
tick_params(axis='both', which='major', labelsize=8)
tick_params(axis='both', which='minor', labelsize=8)
tight_layout()
savefig('GlobalClusterCorr%s.pdf' % conf_fname_mod)

## Figure 3, R^2 of proteins with global cluster
figure(figsize=(5,3))
sets = [(high_corr_prots['weighted_cov']**2).values,(high_corr_prots['normed_cov']**2).values]
hist(sets, stacked = False,label=['Weighted','Normalized'],bins=20)
legend(loc=2, prop={'size':8})
xlabel('R-square of protein with global cluster',fontsize=10)
ylabel('Number of proteins',fontsize=10)
tick_params(axis='both', which='major', labelsize=8)
tick_params(axis='both', which='minor', labelsize=8)
tight_layout()
savefig('GlobalClusterRSquare%s.pdf' % conf_fname_mod)

## Figure 4, coherent scaling of proteins in the global cluster - R^2 comparison between global cluster and specific fits.
def rsq(ys,xs,alpha,beta):
    n = len(xs)
    return 1.0-((ys-(alpha*xs + beta))**2).sum()/((n-1)*ys.var())

def rsq_self(ys,xs):
    alpha,beta,r_val,p_val,std_err = linregress(xs,ys)
    return rsq(ys,xs,alpha,beta)

rsq_global = high_corr_normed[cond_list].apply(lambda x: rsq(x,global_normed[0],1,0),axis=1)
rsq_selfs = high_corr_normed[cond_list].apply(lambda x: rsq_self(x,global_normed[0]),axis=1)

conc_data['alpha'] = conc_data[cond_list].apply(lambda x: linregress(gr/gr.mean(),x/x.mean())[0],axis=1)
conc_data['rsq'] = conc_data[cond_list].apply(lambda x: linregress(gr/gr.mean(),x/x.mean())[2]**2,axis=1)

figure(figsize=(6,3))
p1=subplot(121)
if db_used == 'heinmann':
    if use_LB:
        p1.hist((conc_data[conc_data['gr_cov']>0.6])['alpha'],bins=arange(-2,2,0.1))
    else:
        p1.hist(conc_data['alpha'],bins=arange(-2,2,0.1))
if db_used == 'valgepea':
    p1.hist((conc_data[conc_data['gr_cov']>0.8])['alpha'],bins=arange(-2,2,0.1))
p1.set_xlabel('Normalized response')
p1.axvline(x=0,ymin=0,ymax=100)
p1.axvline(x=0.5,ymin=0,ymax=100)
p1.axvline(x=1,ymin=0,ymax=100)
p1.tick_params(axis='both', which='major', labelsize=8)
p1.tick_params(axis='both', which='minor', labelsize=8)
p2=subplot(122)
ribs = conc_data[conc_data['func']=='Ribosome']
p2.hist(ribs['alpha'],bins=arange(-2,2,0.1))
p2.set_xlabel('Normalized response')
p2.axvline(x=0,ymin=0,ymax=100)
p2.axvline(x=0.5,ymin=0,ymax=100)
p2.axvline(x=1,ymin=0,ymax=100)
p2.tick_params(axis='both', which='major', labelsize=8)
p2.tick_params(axis='both', which='minor', labelsize=8)
tight_layout()
savefig('AllProtsVSRibosomalNormalizedSlopes.pdf')