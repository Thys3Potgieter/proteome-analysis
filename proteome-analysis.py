import csv
import pandas as pd
from pandas.io.parsers import read_csv
from scipy.stats import gaussian_kde,linregress
from scipy import stats
from Bio import SeqIO
from matplotlib.pyplot import hist, savefig, figure,figlegend,legend,plot,xlim,ylim,xlabel,ylabel,tight_layout,tick_params,subplot,subplots_adjust,text,subplots,gcf
from numpy import linspace,ndarray,arange,sum,square,array,cumsum,ones
from numpy.random import randn
from analysis import *
import matplotlib
from math import sqrt,isnan,log
import random
from matplotlib.ticker import FuncFormatter
#import plotly.plotly as py

#py.sign_in("uri.barenholz", "hvi3ma3m30")
### Results generation#####
def get_limits(db):
    if db == 'Heinemann' and not use_LB:
        limits = (0.25,1.)
    if db == 'Heinemann' and use_LB:
        limits = (0.6,1.)
    if db == 'Valgepea':
        limits = (0.8,1.)
    if db == 'Heinemann-chemo':
        limits = (0.8,1.)
    return limits

#Initialize global data structures
dbs = ['Heinemann','Valgepea']
datas = {}
for db in dbs:
    (conds,gr,coli_data) = get_annotated_prots(db) #cond, gr, data
    gr = gr[conds]
    coli_data['avg']=coli_data[conds].mean(axis=1)
    coli_data['std']=coli_data[conds].std(axis=1)
    coli_data = calc_gr_corr(coli_data,conds,gr)
    CV = (coli_data['std']/coli_data['avg']).mean()
    datas[db] = (conds,gr,coli_data)
    print "%s CV: %f" % (db,CV)

#ecoli_data_h = ecoli_data_h[ecoli_data_h['prot']=='Ribosome']
#ecoli_data_v = ecoli_data_v[ecoli_data_v['prot']=='Ribosome']


#write tables data:
def writeCorrsHist(db):
    conds,gr,conc_data = datas[db]
    limits = get_limits(db)
    threshold = limits[0]
    funcs = conc_data['func'].unique()
    func_stat = []
    for func in funcs:
        conc_func = conc_data[conc_data['func']==func]
        corred_idx = conc_func['gr_cov']>threshold
        tot = len(conc_func)
        tot_means = conc_func['avg']
        corr_means = tot_means[corred_idx]
        correlated = len(corr_means)
        func_stat.append(("{%s}" % func,tot,tot_means.sum()*100,correlated,corr_means.sum()*100))
    with open('funcs%s.csv' % db,'wb') as csvfile:
        csvwriter = csv.writer(csvfile,delimiter=';')
        csvwriter.writerow(['Function','Number of proteins','totPrctP','Correlated proteins','corPrctP'])
        for row in func_stat:
            csvwriter.writerow(row)

def writeTopProtsVar(db):
    conds,gr,conc_data = datas[db]
    conc_data = conc_data.copy()
    for cond in conds:
        conc_data[cond]=conc_data[cond]-conc_data['avg']
    conc_data_vars = (conc_data[conds]**2).sum(axis=1)
    conc_data['vars']=conc_data_vars
    tot_vars = conc_data['vars'].sum()
    conc_data = conc_data.sort('avg',ascending=False)
    if db == 'Heinemann':
        conc_data['Temp']=conc_data['protName']
    high_abdc = conc_data.head(20)
    with open('varsOfAbdcs%s.csv' % db,'wb') as csvfile:
        csvwriter = csv.writer(csvfile,delimiter=';')
        csvwriter.writerow(['Function','Sub Function','Name','totPrctP','prctOfVar','cov'])
        j = 0
        for i,row in high_abdc.iterrows():
            csvwriter.writerow((row['func'], row['prot'],row['Temp'],row['avg']*100,row['vars']*100/tot_vars,row['gr_cov']))
            #plot protein with second highest abundance in valgepea data set
            if (j == 1) and (db == 'Valgepea'):
                figure(figsize=(5,3))
                ax = subplot(111)
                ax.plot(gr,100*(row[conds]+row['avg']),'o',label="metE, Correlation: %.2f" % gr.corr(row[conds]))
                ax.set_ylim(0,5)
                ax.set_xlim(0,0.6)
                ax.set_xlabel("Growth rate [$h^{-1}$]")
                ax.set_ylabel("% of total proteome")
                legend(loc=2, prop={'size':8},numpoints=1)
                tight_layout()
                #fig = gcf()
                #py.plot_mpl(fig,filename="metE chemostat")
                savefig('SingleProt%s.pdf' % row['Temp'])
            j+=1
    conc_data = conc_data.sort('vars',ascending=False)
    high_vars = conc_data.head(20)
    with open('varsOfVars%s.csv' % db,'wb') as csvfile:
        csvwriter = csv.writer(csvfile,delimiter=';')
        csvwriter.writerow(['Function','Sub Function','Name','totPrctP','prctOfVar','cov'])
        for i,row in high_vars.iterrows():
            csvwriter.writerow((row['func'], row['prot'],row['Temp'],row['avg']*100,row['vars']*100/tot_vars,row['gr_cov']))

def writeTables():
    for db in dbs:
        writeCorrsHist(db)
        writeTopProtsVar(db)

### Figure 1 - Correlation to growth rate by functional group histogram.
categories = ['Metabolism','Genetic Information Processing','Environmental Information Processing', 'Cellular Processes','NotMapped']
def set_ticks(p,size):
    p.tick_params(axis='both', which='major', labelsize=size)
    p.tick_params(axis='both', which='minor', labelsize=size)

def plot_corr_hist(p,db,conc_data,categories):
    bins = linspace(-1,1,21)
    covs = ndarray(shape=(len(categories),len(bins)-1))
    sets = [] 

    for x in categories:
        sets.append(conc_data[conc_data['group']==x].gr_cov)

    p.hist(sets,bins = bins, stacked = True,label=categories)
    handles,labels=p.get_legend_handles_labels()
    set_ticks(p,8)
    p.set_xlabel('Pearson correlation with growth rate',fontsize=8)
    p.set_ylabel('Number of proteins',fontsize=8)
    for limit in get_limits(db):
        p.axvline(x=limit,ymin=0,ymax=250,ls='--',color='black',lw=0.5)

    #legend(loc=2,prop={'size':8})
    return handles,labels


def plotCorrelationHistograms(dbs,suffix):
    figure(figsize=(5,3))

    coords = {'Heinemann':0.01,'Valgepea':0.625}
    p=subplot(111)
    ps = {'Valgepea':subplot(122)}
    if(len(dbs)>1):
        ps['Heinemann'] = subplot(121)

    for db in dbs:
        conds,gr,conc_data = datas[db]
        plot_corr_hist(ps[db],db,conc_data,categories)
        text(coords[db],0.8,"data from %s et. al." % db,fontsize=8,transform=p.transAxes)

    #assume both subplots have the same categories.
    handles,labels=ps[dbs[0]].get_legend_handles_labels()

    tight_layout()
    figlegend(handles,labels,fontsize=6,mode='expand',loc='upper left',bbox_to_anchor=(0.2,0.8,0.6,0.2),ncol=2)

    subplots_adjust(top=0.83)
    #fig = gcf()
    #py.plot_mpl(fig,filename="Growth rate Correlation histograms")
    savefig('GrowthRateCorrelation%s.pdf' % suffix)

### Figure 3, Global cluster analysis:
def plotGlobalResponse():
    figure(figsize=(5,3))
    colors = {'Heinemann':'blue','Valgepea':'green'}

    for db in dbs:
        conds,gr,coli_data = datas[db]
        glob = get_glob(db,coli_data)
        print "%s global cluster is %d out of %d measured proteins" % (db, len(glob),len(coli_data[coli_data['gr_cov']>-1.]))

        glob_tot = glob[conds].sum()
        alpha,beta,r_val,p_val,std_err = linregress(gr,glob_tot)
        print "global cluster sum follows alpha=%f, beta=%f" % (alpha,beta)
        print "horizontal intercept for %s is %f, corresponding to halflive %f" % (db,-beta/alpha, log(2)*alpha/beta)

        plot(gr.values,glob_tot.values,'o',label="data from %s et. al" % db,color=colors[db])
        plot(gr.values,alpha*gr.values+beta,color=colors[db],label=("%s Trend,$R^2$=%.2f" % (db,gr.corr(glob_tot)**2)))

    xlim(xmin=0.)
    ylim(ymin=0.)
    xlabel('Growth rate [$h^{-1}$]',fontsize=10)
    ylabel('Strongly correlated proteins\n fraction out of proteome',fontsize=10)
    legend(loc=2, prop={'size':8},numpoints=1)
    tick_params(axis='both', which='major', labelsize=8)
    tick_params(axis='both', which='minor', labelsize=8)
    tight_layout()
    #fig = gcf()
    #py.plot_mpl(fig,filename="Global cluster growth rate correlation")
    savefig('GlobalClusterGRFit.pdf')

#gets values at cond_list normalized in y axis
def std_err_fit(gr,s):
    alpha,beta,r,p,st = linregress(gr,s)
    return st
    
def conf_int_min(degfr,s):
    res = stats.t.interval(0.95,degfr,loc=s['alpha'],scale=s['std_err'])
    return  res[0]

def conf_int_max(degfr,s):
    res = stats.t.interval(0.95,degfr,loc=s['alpha'],scale=s['std_err'])
    return  res[1]

def set_std_err(df,gr,cond_list):
    #df['std_err'] = df[cond_list].apply(lambda x: std_err_fit(gr[cond_list]/gr[cond_list].mean(),x/x.mean()),axis=1)
    df['std_err'] = df[cond_list].apply(lambda x: std_err_fit(gr[cond_list],x/x.mean()),axis=1)
    
    df['conf_min'] = df.apply(lambda x: conf_int_min(len(cond_list)-2,x) ,axis=1)
    df['conf_max'] = df.apply(lambda x: conf_int_max(len(cond_list)-2,x) ,axis=1)
    return df

## Figure 2, global cluster slope vs. ribosomal slope
def get_glob(db,df):
    limits = get_limits(db)
    return df[df['gr_cov']>limits[0]]
 
def set_alpha(df,gr,cond_list):
    #df['alpha'] = df[cond_list].apply(lambda x: linregress(gr[cond_list]/gr[cond_list].mean(),x/x.mean())[0],axis=1)
    df['alpha'] = df[cond_list].apply(lambda x: linregress(gr[cond_list],x/x.mean())[0],axis=1)
    return df

def plot_response_hist(db,df,gr,conds,p,total,estimate):
    bins = linspace(-5,5,41)
    xs = linspace(-5,5,200)
    glob_conc = get_glob(db,df)
    glob_conc = set_alpha(glob_conc,gr,conds)
    glob_conc = set_std_err(glob_conc,gr,conds)
    avg = glob_conc['alpha'].mean()
    std_err = glob_conc['std_err'].mean()
    if not total:
        glob_conc_no_ribs = glob_conc[glob_conc['prot'] != 'Ribosome']
        ribs = glob_conc[glob_conc['prot'] == 'Ribosome']
        p.hist([glob_conc_no_ribs['alpha'].values,ribs['alpha'].values],bins=bins,stacked = True,label=['High correlation proteins','Ribosomal proteins'])
    else:
        p.hist(glob_conc['alpha'].values,bins=bins,label=['High correlation proteins'])
    if estimate:
        p.plot(xs,stats.t.pdf(xs,df=len(conds)-2,loc=avg,scale=std_err)*len(glob_conc['alpha'])*0.25)
    p.set_xlim(-5,5)
    for x in range(3):
        p.axvline(x=x,ymin=0,ymax=100,ls='--',color='black',lw=0.5)
    p.set_xlabel('Normalized slope',fontsize=8)
    p.set_ylabel('Number of proteins',fontsize=8)
    set_ticks(p,8)

def plot_response_hist_graphs():
    plots = {"AllProtsNormalizedSlopes":(True,False),"AllProtsVSRibosomalNoExpNormalizedSlopes":(False,False),"AllProtsVSRibosomalNormalizedSlopes":(False,True)}
    for (name,vals) in plots.iteritems():
        figure(figsize=(5,3))
        p = subplot(111)
        ps = {'Heinemann':subplot(121),'Valgepea':subplot(122)}
        coords = {'Heinemann':0.0,'Valgepea':0.62}
        for db in dbs:
            conds,gr,conc_data = datas[db]
            plot_response_hist(db,conc_data,gr,conds,ps[db],vals[0],vals[1])
            text(coords[db],0.93,"data from %s et. al" % db,fontsize=8,transform=p.transAxes)
            handles,labels=ps[db].get_legend_handles_labels()
            if db == 'Valgepea':
                ps[db].set_ylim(0,100)

        figlegend(handles,labels,fontsize=6,mode='expand',loc='upper left',bbox_to_anchor=(0.25,0.8,0.5,0.2),ncol=2)
        tight_layout()
#fig = gcf()
#py.plot_mpl(fig,filename="Normalized slopes distribution")
        savefig('%s.pdf' % name)


#### plot figure of gr corr comparison by ko_num.
#hgr = []
#vgr = []
#only_in_one = 0

#v_ko_vals = set(ecoli_data_v['ko_num'].values)
#h_ko_vals = set(ecoli_data_h['ko_num'].values)
#ko_vals = v_ko_vals.union(h_ko_vals)

#for ko in ko_vals:
#    if ko == 'NotMapped':
#        continue
#    if len((ecoli_data_v[ecoli_data_v['ko_num']==ko])[['gr_cov']].values) >= 1 and len((ecoli_data_h[ecoli_data_h['ko_num']==ko])[['gr_cov']].values) >= 1:
#        vgr.append((ecoli_data_v[ecoli_data_v['ko_num']==ko])[['gr_cov']].values[0][0])
#        hgr.append((ecoli_data_h[ecoli_data_h['ko_num']==ko])[['gr_cov']].values[0][0])
#    else:
#        only_in_one +=1

#figure(figsize=(5,3))

#p=subplot(111)
#p.plot(hgr,vgr,'.')
#p.set_title('%d out of %d are only in one' % (only_in_one, len(ko_vals)))

#savefig('vhcorrcomp.pdf')

# plot Heinemann data only for chemostat conditions.
def heinmann_chemo_plot():
    db = 'Heinemann-chemo'
    figure(figsize=(5,3))
    (cond_list,gr_chemo,ecoli_data_chemo) = get_annotated_prots(db)
    ecoli_data_chemo = calc_gr_corr(ecoli_data_chemo,cond_list,gr_chemo)

    p1=subplot(121)
    p2=subplot(122)
    plot_corr_hist(p1,db,ecoli_data_chemo,categories)

    handles,labels=p1.get_legend_handles_labels()
    figlegend(handles,labels,fontsize=6,mode='expand',loc='upper left',bbox_to_anchor=(0.05,0.8,0.5,0.2),ncol=2)
    glob_chemo = get_glob(db,ecoli_data_chemo)
    print "%s global cluster is %d out of %d measured proteins" % (db, len(glob_chemo),len(ecoli_data_chemo[ecoli_data_chemo['gr_cov']>-1.]))

    glob_tot_chemo = glob_chemo[cond_list].sum()
    alpha,beta,r_val,p_val,std_err = linregress(gr_chemo,glob_tot_chemo)

    print "global cluster sum follows alpha=%f, beta=%f" % (alpha,beta)
    print "horizontal intercept for %s is %f, corresponding to halflive %f" % (db,-beta/alpha, log(2)*alpha/beta)
    p2.plot(gr_chemo.values,glob_tot_chemo.values,'o',label="Heinemann et. al Chem",color='blue')
    p2.plot(gr_chemo.values,alpha*gr_chemo.values+beta,color='blue',label=("Heinemann Chem. Trend,$R^2$=%.2f" % (gr_chemo.corr(glob_tot_chemo)**2)))

    cond_list,gr_v,conc_data = datas['Valgepea']
    glob_v = get_glob("Valgepea",conc_data)
    glob_tot_v = glob_v[cond_list].sum()
    alpha_v,beta_v,r_val,p_val,std_err = linregress(gr_v,glob_tot_v)
    p2.plot(gr_v.values,glob_tot_v.values,'o',label="Valgepea",color='green')
    p2.plot(gr_v.values,alpha_v*gr_v.values+beta_v,color='green',label=("Valgepea Trend,$R^2$=%.2f" % (gr_v.corr(glob_tot_v)**2)))

    p2.set_xlim(xmin=0.)
    p2.set_ylim(ymin=0.)
    p2.set_xlabel('Growth rate',fontsize=8)
    p2.set_ylabel('Strongly correlated proteins\n fraction out of proteome',fontsize=8)
    legend(loc=3, prop={'size':6},numpoints=1)
    set_ticks(p2,8)
    tight_layout()

    subplots_adjust(top=0.83)
#fig = gcf()
#py.plot_mpl(fig,filename="Heinemann chemostat graphs")
    savefig('HeinemannChemostatGr.pdf')

# plot slopes distribution for highly negatively correlated proteins from Valgepea dataset and sum of concentrations
#figure(figsize=(5,3))

#p1=subplot(121)
#p2=subplot(122)

#def get_low_corr(db,df,gr,conds):
#    if db == 'Valgepea':
#        limits = (-1.0,-0.7)
#    glob = df[df['gr_cov']>limits[0]]
#    glob = glob[glob['gr_cov']<limits[1]]
#    print "for db %s anti-correlated cluster is %d out of %d measured proteins" % (db, len(glob.index),len(df.index))
#    glob_tot = glob[conds].sum()
#    alpha,beta,r_val,p_val,std_err = linregress(gr,-glob_tot)
#    return (glob_tot,alpha,beta)

#(neg_corr_v,alpha_neg,beta_neg) = get_low_corr('Valgepea',ecoli_data_v,gr_v,cond_list_v)

#p2.plot(gr_v.values,neg_corr_v.values,'o',label="Valgepea anti correlated")
#p2.plot(gr_v.values,-alpha_neg*neg_corr_v.values+beta_neg,color='blue',label=("Valgepea anti correlated Trend,$R^2$=%.2f" % (gr_v.corr(neg_corr_v)**2)))
#p2.plot(gr_v.values,glob_v.values,'o',label="Valgepea")
#p2.plot(gr_v.values,alpha_v*gr_v.values+beta_v,color='green',label=("Valgepea Trend,$R^2$=%.2f" % (gr_v.corr(glob_v)**2)))

#p2.set_xlim(xmin=0.)
#p2.set_ylim(ymin=0.)
#p2.set_xlabel('Growth rate',fontsize=8)
#p2.set_ylabel('Protein fraction out of proteome',fontsize=8)
#legend(loc=3, prop={'size':6},numpoints=1)
#set_ticks(p2,8)
#tight_layout()

#subplots_adjust(top=0.83)
#savefig('Anticorrelated.pdf')

#check if for 95% of the slopes, the mean of all of the slopes lies in their 95% confidence interval

#Plot variability explained (R^2)/Var? in global cluster and in proteome as function of threshold for HC proteins.

corrs = linspace(-1,1,100)

# calculate variability explained in proteome, take 1 (1 free parameter - selection of global cluster and scaling accordingly.
# calculate variability explained in global cluster, take 2 (1 free parameter - selection of global cluster and measurement of resulting variability reduction.
def square_dist_func(df):
    return df**2

def abs_dist_func(df):
    return abs(df)

def calc_var(f,df,means):
    df = df.copy()
    for col in df.columns:
        df[col]=df[col]-means
    var = f(df)
    var = var.sum().sum()
    return var

def calc_explained_var(f,df,means,gr):
    tot_var = calc_var(f,df,means)
    df = df.copy()
    response = df.sum()
    scaled_response = response/response.mean()
    alpha,beta,r_val,p_val,std_err = linregress(gr,response)
    normed_response = alpha*gr+beta
    normed_response = normed_response/normed_response.mean()
    pred = df.copy()
    scaled = df.copy()
    for col in pred.columns:
        pred[col]=means*normed_response[col]
        scaled[col]=means*scaled_response[col]
    remains = df-pred
    remained_var = calc_var(f,remains,remains.mean(axis=1))
    scaled_remains = df-scaled
    remained_scaled_var = calc_var(f,scaled_remains,scaled_remains.mean(axis=1))
    alpha,beta,r_val,p_val,std_err = linregress(gr,response/response.mean())
    return (alpha,tot_var,tot_var - remained_var,tot_var-remained_scaled_var)

def calc_var_stats(f,conds,gr,glob_conc):
    alphas = []
    glob_data = glob_conc[conds]
    tot_var = calc_var(f,glob_data,glob_conc['avg'])
    print "tot_var is %f" % tot_var
    explained_glob = []
    explained_tot = []
    explained_compl_glob = []
    explained_compl_tot = []
    explained_scaled = []
    glob_frac = []
    for threshold in corrs:
        glob_cluster_idx = glob_conc['gr_cov']>threshold
        glob_compl_idx = glob_conc['gr_cov']<threshold
        alpha,glob_var,glob_explained,glob_scaled_explained = calc_explained_var(f,glob_data[glob_cluster_idx],(glob_conc[glob_cluster_idx])['avg'],gr)
        a,compl_var,compl_explained,compl_scaled_explained = calc_explained_var(f,glob_data[glob_compl_idx],glob_conc[glob_compl_idx]['avg'],gr)
        alphas.append(alpha)
        explained_var = glob_explained/glob_var
        explained_compl_var = compl_explained/compl_var
        explained_tot_frac = glob_explained/tot_var
        explained_compl_tot_frac = compl_explained/tot_var
        explained_scaled_var = (glob_scaled_explained+compl_scaled_explained)/tot_var

        explained_glob.append(explained_var)
        explained_compl_glob.append(explained_compl_var)
        explained_tot.append(explained_tot_frac)
        explained_compl_tot.append(explained_compl_tot_frac)
        explained_scaled.append(explained_scaled_var)
        glob_frac.append(float(len(glob_data[glob_cluster_idx]))/len(glob_data))

    return (explained_glob,explained_tot,explained_compl_glob,explained_compl_tot,explained_scaled,alphas,glob_frac)

def variabilityAndGlobClustSlopes():
    figure(figsize=(5,3))
    ps = {'Heinemann':subplot(121),'Valgepea':subplot(122)}
    alphas = {'Valgepea':[],'Heinemann':[]}
    for db in ['Valgepea','Heinemann']:
        p=ps[db]
        conds,gr,glob_conc = datas[db]
        (explained_glob,explained_tot,explained_compl_glob,explained_compl_tot,explained_scaled,alphas[db],x) = calc_var_stats(square_dist_func,conds,gr,glob_conc)
        p.plot(corrs,explained_glob,markersize=1,label='Explained variability fraction of global cluster')
        p.plot(corrs,explained_tot,markersize=1,label='Explained variability fraction of total data')
        p.plot(corrs,explained_compl_glob,markersize=1,label='Explained complementary variability fraction of global cluster')
        p.plot(corrs,explained_compl_tot,markersize=1,label='Explained complementary variability fraction of total data')
        explained_normed = [x+y for x,y in zip(explained_tot,explained_compl_tot)]
        p.plot(corrs,explained_normed,markersize=1,label='Explained variability fraction when normalizing')
        p.plot(corrs,explained_scaled,markersize=1,label='Explained variability fraction when scaling')
        p.set_ylabel('Explained fraction of variability', fontsize=8)
        p.set_xlabel('global cluster correlation threshold', fontsize=8)
        p.set_ylim(0,1)
        set_ticks(p,6)
        p.axhline(xmin=0,xmax=1,y=0.5,ls='--',color='black',lw=0.5)
        p.legend(loc=2,prop={'size':6})
        p.set_title(db)

    tight_layout()
    #fig = gcf()
    #py.plot_mpl(fig,filename="Non normalized variability statistics")
    savefig('ExpVar2.pdf')

    figure(figsize=(5,3))
    p=subplot(111)
    ps = {'Heinemann':subplot(121),'Valgepea':subplot(122)}
    for db in dbs:
        p = ps[db]
        p.plot(corrs,alphas[db])
        p.set_title(db)
        set_ticks(p,6)
        p.set_ylim(0,2)
    tight_layout()
    #fig = gcf()
    #py.plot_mpl(fig,filename="Global response slope dependence on threshold")
    savefig('ThresholdSlopes.pdf')

def norm_glob_conc(glob_conc,conds):
    glob_conc = glob_conc.copy()
    tot_means = glob_conc['avg']
    for col in conds:
        glob_conc[col] = glob_conc[col]/tot_means
    glob_conc['avg'] = glob_conc[conds].mean(axis=1)
    return glob_conc

def keep_middle(glob_conc,conds):
    glob_conc = glob_conc.copy().sort('avg',ascending=False)
    num = len(glob_conc)
    #glob_conc = glob_conc[:-num/8]
    glob_conc = glob_conc[num/4:]
    return glob_conc

def drop_head(glob_conc,conds,num):
    glob_conc = glob_conc.copy().sort('avg',ascending=False)
    glob_conc = glob_conc[num:]
    return glob_conc

def variablityComparisonHein():
    figure(figsize=(8,5))
    db = 'Heinemann'
    conds,gr,glob_conc = datas[db]
    globs = []
    titles = []
    funcs = [square_dist_func,square_dist_func,square_dist_func,abs_dist_func,abs_dist_func,square]
    globs.append(glob_conc)
    titles.append('all prots')
    globs.append(norm_glob_conc(globs[0],conds))
    titles.append('all prots, normalized')
    globs.append(keep_middle(globs[0],conds))
    titles.append('prots excl. top $\\frac{1}{4}$')
    globs.append(globs[0])
    titles.append('all prots, abs')
    globs.append(globs[2])
    titles.append('prots excl. top $\\frac{1}{4}$, abs')
    globs.append(drop_head(globs[0],conds,10))
    titles.append('prots excl. top 10')
    for i in range(0,6):
        p = subplot(231+i)
        (explained_glob,explained_tot,explained_compl_glob,explained_compl_tot,explained_scaled,temp,x) = calc_var_stats(funcs[i],conds,gr,globs[i])

        p.plot(corrs,explained_glob,markersize=1,label='Explained variability fraction of global cluster')
        p.plot(corrs,explained_tot,markersize=1,label='Explained variability fraction of total data')
        p.plot(corrs,explained_compl_glob,markersize=1,label='Explained complementary variability fraction of global cluster')
        p.plot(corrs,explained_compl_tot,markersize=1,label='Explained complementary variability fraction of total data')
        explained_normed = [x+y for x,y in zip(explained_tot,explained_compl_tot)]
        p.plot(corrs,explained_normed,markersize=1,label='Explained variability fraction when normalizing')
        p.plot(corrs,explained_scaled,markersize=1,label='Explained variability fraction when scaling')
        p.set_ylabel('Explained fraction of variability', fontsize=8)
        p.set_xlabel('global cluster correlation threshold', fontsize=8)
        p.set_ylim(0,1)
        set_ticks(p,6)
        p.axhline(xmin=0,xmax=1,y=0.5,ls='--',color='black',lw=0.5)
        if i==0:
            p.legend(loc=2,prop={'size':6})
        p.set_title(titles[i],fontsize=8)

    tight_layout()
    #fig = gcf()
    #py.plot_mpl(fig,filename="Various heuristics on explained variability for Heinemann data set")
    savefig('ExpVarComp.pdf')

def variabilityAndGlobClustSlopesNormed():
    figure(figsize=(5,3))
    p=subplot(111)
    ps = {'Heinemann':subplot(121),'Valgepea':subplot(122)}
    coords = {'Heinemann':0.03,'Valgepea':0.03}

    alphas = {'Valgepea':[],'Heinemann':[]}
    for db in ['Valgepea','Heinemann']:
        p=ps[db]
        conds,gr,glob_conc = datas[db]
        glob_conc = glob_conc.copy()
        tot_means = glob_conc['avg']
        for col in conds:
            glob_conc[col] = glob_conc[col]/tot_means
        glob_conc['avg'] = glob_conc[conds].mean(axis=1)
        (explained_glob,explained_tot,explained_compl_glob,explained_compl_tot,explained_scaled,alphas[db],glob_frac) = calc_var_stats(square_dist_func,conds,gr,glob_conc)

        p.plot(corrs,explained_glob,markersize=1,label='Explained variability fraction of global cluster')
        p.plot(corrs,explained_tot,markersize=1,label='Explained variability fraction of total data')
        p.plot(corrs,glob_frac,markersize=1,label='Correlated proteins fraction of proteome')
        #p.plot(corrs,explained_compl_glob,markersize=1,label='Explained complementary variability fraction of global cluster')
        #p.plot(corrs,explained_compl_tot,markersize=1,label='Explained complementary variability fraction of total data')
        explained_normed = [x+y for x,y in zip(explained_tot,explained_compl_tot)]
        #p.plot(corrs,explained_normed,markersize=1,label='Explained variability fraction when normalizing')
        #p.plot(corrs,explained_scaled,markersize=1,label='Explained variability fraction when scaling')
        p.set_ylabel('Explained fraction of variability', fontsize=8)
        p.set_xlabel('global cluster correlation threshold', fontsize=8)
        p.set_ylim(0,1)
        set_ticks(p,6)
        p.axhline(xmin=0,xmax=1,y=0.09,ls='--',color='black',lw=0.5)
        #p.axvline(ymin=0,ymax=1,x=get_limits(db)[0],ls='--',color='black',lw=0.5)
        text(coords[db],0.9,"data from %s et. al." % db,fontsize=8,transform=p.transAxes)

    handles,labels=ps['Heinemann'].get_legend_handles_labels()

    figlegend(handles,labels,fontsize=6,loc='upper left',bbox_to_anchor=(0.2,0.8,0.6,0.2))

    tight_layout()
    subplots_adjust(top=0.83)

    #fig = gcf()
    #py.plot_mpl(fig,filename="Explained variability statistics on normalized concentrations")
    savefig('ExpVar3.pdf')

    figure(figsize=(5,3))
    p=subplot(111)
    ps = {'Heinemann':subplot(121),'Valgepea':subplot(122)}
    for db in dbs:
        p = ps[db]
        p.plot(corrs,alphas[db])
        p.set_title(db)
        set_ticks(p,6)
        p.set_ylim(0,2)
    tight_layout()
    #fig = gcf()
    #py.plot_mpl(fig,filename="Dependence on threshold of global response slopes for normalized concentrations")
    savefig('ThresholdSlopes2.pdf')


#6 panel graph - avg. exp. vs norm. slope, slope vs. r^2. non-global cluster avg. exp. vs. slope.
def plotMultiStats(db):
    figure(figsize=(5,3))
    conds,gr,glob_conc = datas[db]
    sp = []
    for i in range(6):
        sp.append(subplot(231+i))

    sp[0].plot(glob_conc['avg'], glob_conc['rsq'],'.', markersize=1)
    sp[0].set_xlabel('Average concentraion', fontsize=6)
    sp[0].set_ylabel('$R^2$ with GR', fontsize=6)

    sp[1].plot(glob_conc['avg'], glob_conc['gr_cov'],'.', markersize=1)
    sp[1].set_xlabel('Average concentraion', fontsize=6)
    sp[1].set_ylabel('Pearson corr. with GR', fontsize=6)

    glob_conc = glob_conc[glob_conc['gr_cov']>get_limits(db)[0]]
    glob_conc = set_alpha(glob_conc,gr,conds)
    glob_conc = set_std_err(glob_conc,gr,conds)

    sp[2].plot(glob_conc['avg'], glob_conc['alpha'],'.', markersize=1)
    sp[2].set_xlabel('Average concentraion (HC prots)', fontsize=6)
    sp[2].set_ylabel('Norm. Slope', fontsize=6)

    sp[3].plot(glob_conc['avg'], glob_conc['std_err'],'.', markersize=1)
    sp[3].set_xlabel('Average concentraion (HC prots)', fontsize=6)
    sp[3].set_ylabel('std err of fit', fontsize=6)

    for i in range(4):
        sp[i].set_xscale('log')

    sp[4].plot(glob_conc['alpha'], glob_conc['std_err'],'.', markersize=1)
    sp[4].set_xlabel('Norm. slope (HC)', fontsize=6)
    sp[4].set_ylabel('std err of fit', fontsize=6)

    sp[5].plot(glob_conc['alpha'], glob_conc['rsq'],'.', markersize=1)
    sp[5].set_xlabel('Norm. slope (HC)', fontsize=6)
    sp[5].set_ylabel('$R^2$ with GR', fontsize=6)

    for i in range(6):
        set_ticks(sp[i],6)
    tight_layout()

    #fig = gcf()
    #py.plot_mpl(fig,filename="Proteins statistics for Heinemann dataset")
    glob_conc.to_csv('stats.csv')
    savefig('AvgConcStats%s.pdf' % db)

#comulative graph - x axis - avg. prot. conc. (or molecule count per cell), y axis, comulative % out of proteome.
def plotComulativeGraph():
    figure(figsize=(5,3))
    sp = [subplot(121),subplot(122)]

    conds,gr,coli_data = datas['Heinemann']
    avgs = sorted(coli_data['avg'].values)

    sp[0].plot(avgs,cumsum(avgs),'.',markersize=0.5)
    sp[0].set_xlabel('Avg. prot. conc.',fontsize=6)
    sp[0].set_xscale('log')

    sp[1].plot(arange(0,len(avgs)),cumsum(avgs),'.',markersize=0.5)
    sp[1].set_xlabel('num. of prots',fontsize=6)

    for i in range(2):
        sp[i].set_ylabel('accumulated fraction \n out of proteome',fontsize=6)
        sp[i].axhline(xmin=0,xmax=i*2000+1,y=0.05,ls='--',color='black',lw=0.5)
        sp[i].axhline(xmin=0,xmax=i*2000+1,y=0.01,ls='--',color='black',lw=0.5)
        set_ticks(sp[i],6)

    tight_layout()
    #fig = gcf()
    #py.plot_mpl(fig,filename="Cumulative proteome concentration distribution for Heinemann")
    savefig('DistStatsHein.pdf')

#plot the graphs for the 10 highest abundance proteins with their descriptions.
def plotHighAbundance():
    figure(figsize=(5,3))
    ps = {'Heinemann':subplot(121),'Valgepea':subplot(122)}
    for db in dbs:
        p = ps[db]
        conds,gr,coli_data = datas[db]
        coli_data = coli_data.copy()
        if db == 'Heinemann':
            coli_data['ID']=coli_data['protName']
        coli_data = coli_data.sort('avg',ascending=False)
        coli_data_conds = coli_data[conds]
        coli_data_conds = coli_data_conds.head(7)
        for i in coli_data_conds.index:
            desc = coli_data.ix[i]
            desc = "%s: %s: %s" % (desc['func'],desc['prot'],desc['ID'])
            p.plot(gr.values,coli_data_conds.ix[i].values,label=('%s' % desc))
        p.legend(loc=2, prop={'size':3},numpoints=1)
        p.set_ylim(0,0.1)
    tight_layout()
    #fig = gcf()
    #py.plot_mpl(fig,filename="Most abundant proteins concentration vs growth rate")
    savefig('highest.pdf')

def plotRibosomal():
    figure(figsize=(5,3))
    ps = {'Heinemann':subplot(121),'Valgepea':subplot(122)}
    for db in dbs:
        p = ps[db]
        conds,gr,coli_data = datas[db]
        coli_data = coli_data.copy()
        if db == 'Heinemann':
            coli_data['ID']=coli_data['protName']
        coli_data = coli_data[coli_data['prot']=='Ribosome']
        coli_data_conds = coli_data[conds].copy()
        tot = coli_data_conds.sum()
        means = coli_data_conds.mean(axis=1)
        for col in conds:
            coli_data_conds[col] = coli_data_conds[col]/means
        for i in coli_data_conds.index:
            desc = coli_data.ix[i]
            desc = "%s" % (desc['ID'])
            p.plot(gr.values,coli_data_conds.ix[i].values,label=('%s' % desc))
        tot = tot/tot.mean()
        p.plot(gr.values,tot,'o')
        p.set_ylim(0,3)
    tight_layout()
    #fig = gcf()
    #py.plot_mpl(fig,filename="Ribosomal proteins concentration vs growth")
    savefig('ribosomal.pdf')


#randomly select a few proteins and plot their prediction vs the actual concentration of a different protein in the HC prots.
def plotPrediction():
    for db in dbs:
        figure(figsize=(5,5))
        conds,gr,coli_data = datas[db]
        glob = get_glob(db,coli_data)
        for i in range(1,10):
            p = subplot(330+i)
            samp = random.sample(glob.index,11)
            pred = samp[0:-1]
            est = samp[-1]
            pred = glob.ix[pred]
            est = glob.ix[est]
            pred = pred[conds].sum()
            pred = pred/pred.mean()
            est = est[conds]
            est = est/est.mean()
            alpha,beta,r_val,p_val,std_err = linregress(gr,pred)
            linpred = {}
            for c in gr.index:
                linpred[c]=alpha*gr[c]+beta
            linpred = pd.Series(linpred)
            linpred = linpred[conds]
            p.plot(gr.values,linpred.values,color='blue')
            p.plot(gr.values,pred,'o',color='blue',markersize=2)
            p.plot(gr.values,est,'o',color='green',markersize=2)
            p.set_ylim(0,3)
            p.set_xlim(0,0.7)
            set_ticks(p,8)
            p.set_title("$R^2$=%.2f" % est.corr(linpred)**2,fontsize=8)
        tight_layout()    
        #fig = gcf()
        #py.plot_mpl(fig,filename="Random proteins estimations, 10 proteins at a time, %s" % db)
        savefig('RandEstimate%s.pdf' % db)

#plot ribosomal proteins vs. global cluster proteins with trendlines and R^2 estimates.
def plotRibosomalVsGlobTrend():
    figure(figsize=(5,3))
    ps = {'Heinemann':subplot(121),'Valgepea':subplot(122)}
    coords = {'Heinemann':0.03,'Valgepea':0.03}
    for db in dbs:
        conds,gr,coli_data = datas[db]
        glob = get_glob(db,coli_data)
        no_ribs = glob[glob['prot'] != 'Ribosome']
        ribs = glob[glob['prot'] == 'Ribosome']
        colors = ['blue','green']
        p = ps[db]
        ser = ['Non ribosomal proteins','Ribosomal proteins']
        for j,d in enumerate([no_ribs,ribs]):
            c = colors[j]
            d = d[conds].sum()
            d = d/d.mean()
            p.plot(gr.values,d.values,'o',color=c,label=ser[j])
            alpha,beta,r_val,p_val,std_err = linregress(gr,d)
            p.plot(gr.values,alpha*gr.values+beta,color=c,label="Trend line $R^2$=%.2f" % (gr.corr(d)**2))
            p.set_xlim(xmin=0.)
            p.set_ylim(ymin=0.)
            p.set_xlabel('Growth rate',fontsize=10)
            p.set_ylabel('Normalized concentration',fontsize=10)
        p.legend(loc='lower left', prop={'size':8},numpoints=1)
        set_ticks(p,8)
        text(coords[db],0.93,"data from %s et. al" % db,fontsize=8,transform=p.transAxes)
    tight_layout()
    #fig = gcf()
    #py.plot_mpl(fig,filename="Ribosomal proteins vs global cluster")
    savefig('RibsVsGlob.pdf')

        
writeTables()
#Single histogram for presentation
plotCorrelationHistograms(["Valgepea"],"Val")
plotCorrelationHistograms(dbs,"")
plotGlobalResponse()
plot_response_hist_graphs()
heinmann_chemo_plot()
plotMultiStats('Valgepea')
plotComulativeGraph()
plotHighAbundance()
plotPrediction()        
variabilityAndGlobClustSlopes()
variabilityAndGlobClustSlopesNormed()
variablityComparisonHein()
plotRibosomal()
plotRibosomalVsGlobTrend()
