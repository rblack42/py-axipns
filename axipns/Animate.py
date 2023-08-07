import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class DisplayProperty(object):
    ''' set up property animation display'''
    propName = [
        "neta",
        "Density",
        "Axial Velocity",
        "Radial Velocity",
        "Static Pressure",
        "Static Temperature",
        "Mach Number",
        "Total Pressure",
    ]

    current_item = 0
    # create data array for plotting selected property
    data = np.zeros(31) 
    raw_data = []

    def __init__(self, prop=7):
        '''property number selects property to display'''
        self.prop = prop
        self.loadDataFile(prop)

        # graphics setup
        fig, ax = plt.subplots()
        self.ax = ax
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1) 
        self.ax.grid(True)


    def __call__(self,i):
        if i == 0:
            self.line.set_data = ([],[])
        x = self.load_property()
        self.line.set_data(x,self.y)
        return self.line

    def load_prop(self):
        x = []
        for i in range(31):
            x[i] = self.raw_data[self.current_index]
            self.currrent_index = self.current_index + 1
        self.data = x

    def loadDataFile(self, pnum):
        '''read selected property from output file'''
        print("Processing %s" % self.propName[self.prop])
        rdata = np.zeros(8)
        fin = open("solution.dat","r")
        while fin:
            line = fin.readline()
            
            if line == "": break
            if line.startswith("A"): continue
            i,r,u,v,p,T,M,pt = line.split()
            rdata[0] = int(i)       # neta
            rdata[1] = float(r)     # rho
            rdata[2] = float(u)     # u
            rdata[3] = float(v)     # v
            rdata[4] = float(v)     # p
            rdata[5] = float(T)     # T
            rdata[6] = float(M)     # M
            rdata[7] = float(pt)    # pT
            self.raw_data.append(rdata[self.prop])
        fin.close()

    def run(self):
        '''begin animation run'''
        fig, ax = plt.subplots()
        ud = UpdateProp(ax)
        anim = FuncAnimation(fig, ud, frames=100, interval=100,blit=True)
        plt.show()


class UpdateProp(object):
        '''used by mp FuncAnimation'''
        
        def __init__(self, ax):
            self.ax = ax
            self.line = ax.plot([],[],'k-')
            self.y = np.linspace(0,1,31)

if __name__ == '__main__':
    disp = DisplayProperty(6)
    disp.run()
