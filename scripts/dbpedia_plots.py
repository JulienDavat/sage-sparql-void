from argparse import ArgumentParser, ArgumentTypeError
from seaborn import barplot
from pandas import read_csv
import numpy as np
import matplotlib.pyplot as plt

# ====================================================================================================
# ===== Command line interface =======================================================================
# ====================================================================================================

parser = ArgumentParser()
parser.add_argument("--input", "-i", help="The file that contains queries evaluation statistics", default=None)
parser.add_argument("--output", "-o", help="The path of the file in which the figure will be saved", default=None)
args = parser.parse_args()

input_file = args.input
output_file = args.output

if input_file is None or output_directory is None:
    print('Error: missing required arguments ! USAGE: dbpedia_plots.py --input <data> --output <output>')
    exit(1)

# ====================================================================================================
# ===== Figures construction =========================================================================
# ====================================================================================================

def transform_ms_to_sec(data):
    data['execution_time'] = data['execution_time'].div(1000)

def transform_bytes_to_kbytes(data):
    data['data_transfer'] = data['data_transfer'].div(1024)

# def sort_by_approach(data):
#     data.loc[data['approach'] == 'Virtuoso', 'order'] = 1
#     data.loc[data['approach'] == 'Jena-Fuseki', 'order'] = 2
#     data.loc[data['approach'] == 'SaGe-PTC-20', 'order'] = 3
#     data.loc[data['approach'] == 'SaGe-PTC-5', 'order'] = 4
#     data.loc[data['approach'] == 'SaGe-Multi', 'order'] = 5
#     return data.sort_values(by=['order', 'query'])

def plot_metric(ax, data, metric, title, xlabel, ylabel, logscale=False):
    chart = barplot(x='query', y=metric, hue='approach', data=data, ax=ax)
    if logscale:
        chart.set_yscale("log")
    chart.set_title(title)
    chart.set_xlabel(xlabel)
    chart.set_ylabel(ylabel)
    chart.legend().set_title('')

def create_figure(data, logscale=False):
    # initialization of the figure
    fig = plt.figure(figsize=(12, 4))
    plt.subplots_adjust(wspace=0.25)
    # creation of the left part (SP workload)
    ax1 = fig.add_subplot(121)
    plot_metric(ax1, data, 'execution_time', '', '', 'Execution Time (ms)', logscale=logscale)
    plt.legend().remove()
    fig.legend(loc='upper center', bbox_to_anchor=(0.5, 0.99), fancybox=True, shadow=True, ncol=5)
    ax2 = fig.add_subplot(122)
    plot_metric(ax2, data, 'data_transfer', '', '', 'Traffic (KBytes)', logscale=logscale)
    plt.legend().remove()
    plt.show()
    return fig

dataframe = read_csv(input_file, sep=',')
print(dataframe)
transform_bytes_to_kbytes(dataframe)

# sorted_dataframe = sort_by_approach(dataframe)
# print(sorted_dataframe)

figure = create_figure(dataframe, logscale=True)
figure.savefig(output_file)