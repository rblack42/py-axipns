class FreeStream(object):

    def __init__(self):
        '''create free stream instance'''
        p = {
                "M_infty":      5.95,
                "rho_infty":    1.0,
                "u_infty":      1.0,
                "v_infty":      0.0,
                "gamma":        1.4,
        }
        p["p_infty"] = \
            p["rho_infty"] * \
            p["u_infty"]**2/ \
            p["M_infty"]**2
        p["T_infty"] = \
            p["gamma"]*p["p_infty"] / \
            ((p["gamma"] - 1.0)*p["rho_infty"])
        p["H_infty"] = \
            p["T_infty"] + 0.5*p["u_infty"]**2
        self.fs_props = p

    def Initialize(self):
        return(self.fs_props)

if __name__ == '__main__':
    fs = FreeStream()
    props = fs.Initialize()
    for p in props:
        print(p,props[p])
