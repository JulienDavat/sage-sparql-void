from argparse import ArgumentParser, ArgumentTypeError
from seaborn import barplot
from pandas import read_csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ====================================================================================================
# ===== Command line interface =======================================================================
# ====================================================================================================

parser = ArgumentParser()
parser.add_argument("--input", "-i", help="The file that contains queries evaluation statistics", default=None)
parser.add_argument("--output", "-o", help="The path of the file in which the figure will be saved", default=None)
args = parser.parse_args()

input_file = args.input
output_file = args.output

if input_file is None or output_file is None:
    print('Error: missing required arguments ! USAGE: dbpedia_plots.py --input <file> --output <file>')
    exit(1)

# ====================================================================================================
# ===== Figures construction =========================================================================
# ====================================================================================================

def transform_ms_to_sec(data):
    data['execution_time'] = data['execution_time'].div(1000)

def transform_bytes_to_Mbytes(data):
    data['data_transfer'] = data['data_transfer'].div(1048576)

def sort_by_name(data):
    data['order'] = data['query'].str[1:].astype(int)
    return data.sort_values(by=['order'])

def plot_metric(ax, data, metric, title, xlabel, ylabel, logscale=False, display_x=True):
    chart = barplot(x='query', y=metric, hue='approach', data=data, ax=ax)
    if logscale:
        chart.set_yscale("log")
    chart.set_title(title)
    chart.set_xlabel(xlabel)
    chart.set_ylabel(ylabel)
    chart.legend().set_title('')
    if not display_x:
        chart.set(xticklabels=[])
    # Makes queries label more readable
    chart.set_xticklabels(
        chart.get_xticklabels(),
        rotation=90, 
        horizontalalignment='center',
        fontweight='light',
        fontsize='large'
    )
    # Makes the difference between queries with or without a DISTINCT modifier
    for xtick in chart.get_xticklabels():
        if xtick.get_text() in ['Q1', 'Q6', 'Q11', 'Q14', 'Q17', 'Q18']:
            xtick.set_color('black')
        else:
            xtick.set_color('blue')

def create_figure(data, logscale=False):
    # initialization of the figure
    fig = plt.figure(figsize=(12, 4.5))
    plt.subplots_adjust(wspace=0.25)
    # creates of the left part (execution time)
    ax1 = fig.add_subplot(121)
    plot_metric(ax1, data, 'execution_time', '', '', 'Execution Time (sec)', logscale=logscale)
    ax1.axhline(60, ls='--', color='darkred')
    plt.legend().remove()
    # creates of the left part (data transfer)
    ax2 = fig.add_subplot(122)
    plot_metric(ax2, data, 'data_transfer', '', '', 'Traffic (MBytes)', logscale=logscale)
    plt.legend().remove()
  
    # creates the legen
    handles, labels = ax1.get_legend_handles_labels()
    timeout = plt.Line2D((0,1),(0,0), linestyle='--', color='darkred', label='Virtuoso timeout (60s)')
    handles.append(timeout)
    plt.figlegend(handles=handles, loc='upper center', bbox_to_anchor=(0.5, 0.99), fancybox=True, shadow=True, ncol=5)

    plt.show()
    return fig

# def create_figure(data, logscale=False):
#     sp_workload = data[(data['workload'] == 'SP')]
#     sp_nd_workload = data[(data['workload'] == 'SP-ND')]
#     # initialization of the figure
#     fig = plt.figure(figsize=(14, 8))
#     plt.subplots_adjust(hspace=0.1)
#     # creation of the left part (SP workload)
#     ax1 = fig.add_subplot(221)
#     plot_metric(ax1, sp_workload, 'execution_time', '', '', 'Execution Time (sec)', logscale=logscale, display_x=False)
#     ax1.axhline(60, ls='--', color='darkred')
#     plt.legend().remove()
#     fig.legend(loc='upper center', bbox_to_anchor=(0.5, 0.97), fancybox=True, shadow=True, ncol=5)
#     ax2 = fig.add_subplot(223)
#     plot_metric(ax2, sp_workload, 'data_transfer', '', '', 'Traffic (KBytes)', logscale=logscale)
#     plt.legend().remove()
#     # creattion of the right part (SP-ND workload)
#     ax3 = fig.add_subplot(222)
#     plot_metric(ax3, sp_nd_workload, 'execution_time', '', '', '', logscale=logscale, display_x=False)
#     ax3.axhline(60, ls='--', color='darkred')
#     plt.legend().remove()
#     ax4 = fig.add_subplot(224)
#     plot_metric(ax4, sp_nd_workload, 'data_transfer', '', '', '', logscale=logscale)
#     plt.legend().remove()
    
#     plt.show()
#     return fig

dataframe = read_csv(input_file, sep=',')
print(dataframe)
transform_bytes_to_Mbytes(dataframe)

figure = create_figure(sort_by_name(dataframe), logscale=True)
figure.savefig(output_file)