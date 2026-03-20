import sys
import numpy as np
from matplotlib import pyplot as plt
from distrib_funcs import *
from matplotlib.patches import Rectangle
from matplotlib import ticker as mtick
from matplotlib import colors as mcolors
import random
# Set the default font size for all elements to 14
plt.rc('font', size=14)

P_peak = 100e6 # peak throughput MUPS
n_half = 3e6 # number of points needed to saturate GPU
latency = 5e-6 # micro-seconds of latency
bandwidth = 100e6 # GB/s inifini band
nvar=8
double_size = 8
beta = nvar*double_size/(bandwidth)
C_ghost = 6

def get_optimal_time(p, meshvals):
    return (sum(meshvals) / p + n_half) / P_peak

def calculate_time(distrib, meshes):
    
    # determine groups
    groups = {}
    used = set()
    rank_groups = [[] for _ in range(len(distrib))]
    for i in range(len(distrib)):
        rank = distrib[i]
        for j in range(len(rank)):
            mesh = rank[j]
            if mesh in used:
                continue
            common_groups = [i]
            for k in range(i+1, len(distrib)):
                if mesh in distrib[k]:
                    common_groups.append(k)
            if tuple(common_groups) in groups:
                groups[tuple(common_groups)].add(mesh)
                used.add(mesh)
            else:
                groups[tuple(common_groups)] = set([mesh])
                for cg in common_groups:
                    rank_groups[cg].append(common_groups)
                    used.add(mesh)
    
    #print(groups)

    # function to evaluate compute time for a group
    def get_time(mesh_group):
        sizes = [meshes[i] for i in groups[mesh_group]]
        cuts = len(mesh_group) - 1
        time = 0
        for size in sizes:
            NbyP = size/(cuts+1)
            if cuts==0:
               betax=0
               alphax=0
            else:
                betax=beta
                alphax=1
            time += (1/P_peak)*((NbyP + C_ghost*(NbyP)**(2/3)) + n_half) + betax*(NbyP)**(2/3) + alphax*latency
        return time

    # determine if groups are valid (exclusive)
    #duplicates = False
    #cur = set()
    #for k in groups.keys():
    #    for m in groups[k]:
    #        if m in cur:
    #            duplicates = True
    #            break
    #        else:
    #            cur.add(m)
    #    if duplicates:
    #        break
    #if duplicates:
    #    print('Error - complex mesh distribution is impossible to execute in parallel with simple methods')
    #    return sum(meshes)
    
    # find total time for each rank
    times = [0 for _ in range(len(distrib))]
    group_ranks = sorted([(len(i), i) for i in groups.keys()], reverse=True)
    #print(group_ranks)
    mask = [False for _ in range(len(group_ranks))]
    for i in range(len(mask)):
        curlayer = set()
        for j in range(i, len(mask)):
            if mask[j]:
                continue
            cur = group_ranks[j][1]
            broken = False
            for ridx in cur:
                if ridx in curlayer:
                    broken = True
                    break
            if broken:
                continue
            for ridx in cur:
                curlayer.add(ridx)
            largest = max([times[ridx] for ridx in cur])
            group_time = largest + get_time(cur)
            for ridx in cur:
                times[ridx] = group_time
            mask[j] = True

    #print(times)

    # return maximum time
    return max(times)


#bins = 10
#meshes = [1000, 1000, 500, 500, 800, 200, 200, 200, 10000, 300, 300, 300, 450, 450, 450]

#distrib = no_split_distrib(bins, meshes)
#print(distrib)
#print(calculate_time(distrib, meshes))


def heatmap(ax, func, minbin, maxbin, minmesh, maxmesh, resolution, probfunc, worstcol=np.array([1, 0, 0]), 
            bestcol=np.array([0,1,0]), worstlbc=0.8, bestlbc=1, num_tests=20, colorbar=None, title=None):
    bins = minbin + np.arange(0, resolution) * (maxbin - minbin) / (resolution - 1)
    meshes = minmesh + np.arange(0, resolution) * (maxmesh - minmesh) / (resolution - 1)
    colors = np.empty(shape=(resolution, resolution))
    for i in range(resolution):
        for j in range(resolution):
            avg_lbc = 0
            for k in range(num_tests):
                curbins, curmeshes = int(bins[i]), int(meshes[j])
                meshvals = [probfunc() for _ in range(curmeshes)]
                result = calculate_time(func(curbins, meshvals), meshvals)
                optimal = get_optimal_time(curbins, meshvals)
                lbc = optimal / result
                avg_lbc += lbc
            avg_lbc /= num_tests
            colors[i, j] = avg_lbc
    halfbox_bin = (maxbin - minbin) / (2*(resolution - 1))
    halfbox_mesh = (maxmesh - minmesh) / (2*(resolution-1))
    plot_extent = [minbin - halfbox_bin, maxbin + halfbox_bin, minmesh - halfbox_mesh, maxmesh + halfbox_mesh]
    cmap = plt.cm.RdYlGn
    norm = mcolors.Normalize(vmin=worstlbc, vmax=bestlbc)
    im = ax.imshow(colors, extent=plot_extent, cmap=cmap, norm=norm)
    ax.set_xticks(bins)
    ax.set_yticks(meshes)
    ax.set_xlabel('number of processors')
    ax.set_ylabel('number of meshes')
    ax.set_aspect(halfbox_bin / halfbox_mesh)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f'{int(x)}'))
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f'{int(x)}'))
    if not (colorbar is None):
        ax.get_figure().colorbar(im, ax=colorbar, label='parallel efficiency')
    if not (title is None):
        ax.set_title(title)

def line_plot(ax, funcs, labels, ri, rf, num_rtests, pi, pf, num_ptests, pdf, num_tests=20):
    xdata = []
    ydata = [[] for _ in range(len(funcs))]
    dr = (rf - ri) / (num_rtests - 1)
    dp = (pf - pi) / (num_ptests - 1)
    curr = ri
    for i in range(num_rtests):
        curp = pi
        avgs = [0 for _ in range(len(funcs))]
        count = 0
        for j in range(num_ptests):
            curm = int(curp * curr)
            if curm < 1:
                curp = int(curp + dp)
                continue
            for test in range(num_tests):
                meshvals = [pdf() for _ in range(curm)]
                optimal = get_optimal_time(curp, meshvals)
                for k in range(len(funcs)):
                    result = calculate_time(funcs[k](curp, meshvals), meshvals)
                    avgs[k] += optimal / result
                count += 1
            curp = int(curp + dp)
        xdata.append(curr)
        for k in range(len(funcs)):
            ydata[k].append(avgs[k] / count)
        curr += dr
    for k in range(len(funcs)):
        ax.plot(xdata, ydata[k], label=labels[k])
    ax.set_xlabel('Ratio of number of meshes to processors')
    ax.set_ylabel('Parallel efficiency')
    ax.legend()

def winners(ax, funcs, names, pdf_p, pdf_m, pdf_sizes, trials, title):
    vals = [0 for _ in range(len(funcs))]
    for _ in range(trials):
        p = int(pdf_p())
        m = int(pdf_m())
        meshvals = [pdf_sizes() for mi in range(m)]
        optimal = get_optimal_time(p, meshvals)
        best = (-1, 0)
        for k in range(len(funcs)):
            result = calculate_time(funcs[k](p, meshvals), meshvals)
            lbc = optimal / result
            if lbc > best[1]:
                best = (k, lbc)
        vals[best[0]] += 1
    bar = ax.bar(names, vals)
    ax.bar_label(bar)
    ax.set_title(title)

def tolerance_plot(ax, funcs, names, mintol, matol, step, p, m, s, trials=500):
    t = mintol
    xvals = []
    yvals = [[] for _ in range(len(funcs))]
    while t <= matol:
        avgs = [0 for _ in range(len(funcs))]
        for trial in range(trials):
            cp = int(p())
            cm = int(m())
            meshvals = [s() for _ in range(cm)]
            optimal = get_optimal_time(cp, meshvals)
            for k in range(len(funcs)):
                result = calculate_time(funcs[k](cp, meshvals, tol=t), meshvals)
                avgs[k] += optimal / result
        for k in range(len(funcs)):
            yvals[k].append(avgs[k] / trials)
        xvals.append(t)
        t += step
    for i in range(len(funcs)):
        ax.plot(xvals, yvals[i], label=names[i])
    ax.legend()
    ax.set_xlabel('tolerance')
    ax.set_ylabel('parallel efficiency')

def show_distrib(distrib):
    pass

def uniform_pdf(mi, ma):
    return random.random() * (ma - mi) + mi

fig, axs = plt.subplots(2, 2)

#heatmap(axs[0, 0], over_cut, 4, 30, 4, 100, 15, lambda: uniform_pdf(1e6, 5e7), worstlbc=0, title='Uniform')
#heatmap(axs[0, 1], no_split_distrib, 4, 30, 4, 100, 15, lambda: uniform_pdf(1e6, 5e7), worstlbc=0, title='Greedy')
#heatmap(axs[1, 0], split_distrib, 4, 30, 4, 100, 15, lambda: uniform_pdf(1e6, 5e7), worstlbc=0, title='Group')
#heatmap(axs[1, 1], split_distrib2, 4, 30, 4, 100, 15, lambda: uniform_pdf(1e6, 5e7), worstlbc=0, colorbar=[axs[0, 0], axs[0, 1], axs[1, 0], axs[1, 1]], title='Singleton-Group')

fig, ax = plt.subplots()

line_plot(ax, [over_cut, no_split_distrib, split_distrib, split_distrib2], ['Uniform', 'Greedy', 'Grouping', 'Singleton-Group'], 0.25, 5, 50, 4, 32, 14, lambda: uniform_pdf(1e6, 5e7))

fig, ax = plt.subplots()

#winners(ax, [over_cut, no_split_distrib, split_distrib, split_distrib2], ['Uniform', 'Greedy', 'Grouping', 'Singleton-Group'], 
#        lambda: uniform_pdf(4, 32), lambda: uniform_pdf(5, 50), lambda: uniform_pdf(1e6, 5e7), 10000, 'Number of times each algorithm performed the best over 10000 trials')

fig, ax = plt.subplots()

tolerance_plot(ax, [split_distrib, split_distrib2], ['Grouping', 'Singleton-Group'], 0.01, 1, 0.01, 
               lambda: uniform_pdf(4, 32), lambda: uniform_pdf(5, 50), lambda: uniform_pdf(1e6, 5e7))

plt.show()







