from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
from distrib_funcs import no_split_distrib, split_distrib, split_distrib2, over_cut
import sys
import random
from distinctipy import distinctipy

class Mesh:

    def __init__(self, width, height, color):
        self.w = width
        self.h = height
        self.col = color

    def goto(self, poslist, ax, horiz=False):
        newh = self.h / len(poslist)
        if horiz:
            for pos in poslist:
                ax.add_patch(Rectangle((pos[0], pos[1] - self.w * 0.5), newh, self.w, edgecolor='black', facecolor=self.col, linewidth=2))
        else:
            for pos in poslist:
                ax.add_patch(Rectangle((pos[0] - self.w * 0.5, pos[1]), self.w, newh, edgecolor='black', facecolor=self.col, linewidth=2))

class Bin:
    
    def __init__(self, width):
        self.w = width

    def draw(self, pos, ax):
        left = (pos[0] - self.w/2, pos[1])
        right = (pos[0] + self.w/2, pos[1])
        leftup = (left[0] - self.w * 0.1, left[1] + self.w * 0.2)
        rightup = (right[0] + self.w * 0.1, right[1] + self.w * 0.2)
        points = [leftup, left, right, rightup]
        x = []
        y = []
        for xc, yc in points:
            x.append(xc)
            y.append(yc)
        ax.plot(x, y, color='black', linewidth=5)

def draw_arrangement(sizes, distrib, boundrect, ax, colors=None):
    numbins = len(distrib)
    ideal = sum(sizes) / numbins
    binwidth = (boundrect[2] / numbins) * 0.6
    counts = [0 for _ in range(len(sizes))]
    for i in distrib:
        for j in i:
            counts[j] += 1
    best = (0, -1)
    for i in range(0, len(distrib)):
        cursize = 0
        for j in distrib[i]:
            cursize += sizes[j] / counts[j]
        if cursize > best[1]:
            best = (i, cursize)
    fact = (boundrect[3] * 0.9 - boundrect[3] * 0.015 * (len(distrib[best[0]]) - 1)) / best[1]
    counts = [0 for _ in range(len(sizes))]
    for i in distrib:
        for j in i:
            counts[j] += 1
    meshes = []
    if colors is None:
        colors = distinctipy.get_colors(len(sizes))
        print(colors)
    for i in range(len(sizes)):
        size = sizes[i]
        col = colors[i]
        meshes.append(Mesh(binwidth * 0.9, fact * size, col))
    binobj = Bin(binwidth)
    poses = [[] for _ in range(len(meshes))]
    bindist = binwidth * 2
    startdist = (boundrect[2] - bindist * (numbins - 1)) * 0.5
    for i in range(len(distrib)):
        cur = distrib[i]
        x = startdist + bindist * i
        y = boundrect[1] + boundrect[3] * 0.03
        binobj.draw((x, boundrect[1]), ax)
        for j in cur:
            poses[j].append((x, y))
            y += meshes[j].h / counts[j] + boundrect[3] * 0.015
    for i in range(len(meshes)):
        meshes[i].goto(poses[i], ax)
    y = (boundrect[1] + boundrect[3] * 0.03 + ideal * fact) + boundrect[3] * 0.025
    ax.plot([boundrect[0] - boundrect[2] * 0.05, boundrect[0] + boundrect[2] * 1.05], [y, y], 'r--')

sizes = [int(i) for i in sys.argv[2:]]
#distrib = [i[::-1] for i in split_distrib2(int(sys.argv[1]), sizes)]
#print(distrib)
distrib = [[0, 4, 1], [0, 4, 6, 5], [0, 4, 9, 3], [0, 4, 8, 7, 2]]
fig, ax = plt.subplots()
ax.set_xlim(-0.1, 1.1)
ax.set_ylim(-0.1, 1.1)
ax.set_aspect('equal')
draw_arrangement(sizes, distrib, (0, 0, 1, 0.65), ax, [(0.0, 1.0, 0.0), (1.0, 0.0, 1.0), (0.0, 0.5, 1.0), (1.0, 0.5, 0.0), (0.5, 0.75, 0.5), (0.33298390671014944, 0.01121865616709794, 0.6569712846901441), (0.9404013272010967, 0.01059245534252684, 0.23684611431675995), (0.05551430897103471, 0.9980266011983393, 0.9146500272919957), (0.892048854173943, 0.9974287000330913, 0.038370476620278926), (0.0017974775205026328, 0.5013509525842756, 0.15216521476682776)])
plt.show()


        

            




