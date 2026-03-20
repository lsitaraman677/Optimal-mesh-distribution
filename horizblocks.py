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

a = Mesh(1, 10, 'green')
b = Mesh(1, 5, 'blue')
c = Mesh(1, 4, 'red')
d = Mesh(1, 2, 'cyan')
e = Mesh(1, 2, 'yellow')
f = Mesh(1, 2, 'magenta')

fig, ax = plt.subplots()
a.goto([(0, 0)], ax, horiz=True)
b.goto([(0, 1.5)], ax, horiz=True)
c.goto([(0, 3)], ax, horiz=True)
d.goto([(0, 4.5)], ax, horiz=True)
e.goto([(0, 6)], ax, horiz=True)
f.goto([(0, 7.5)], ax, horiz=True)

ax.set_xlim(-1, 11)
ax.set_ylim(-1, 8.5)

plt.show()
        

            




