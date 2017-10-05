#!/usr/bin/python
#
# We are solving the scheduling problem for compute dense kernels by focusing
# on the microarchitecture of the target processor. Even though these are OOO
# processors, we treat this underlying system as a VLIW machine and schedule
# our code accordingly.
#
# This program implements the OASIC model for scheduling VLIW programs using
# Integer Linear Programming.
#
#
# - Richard Michael Veras
#   rveras@cmu.edu




#################
# MODEL OBJECTS #
#################

#### Resource Graph ####
# G_R = ( N_R, E_R ) DAG Partitite
# N_R = N_I \union N_R^F
# N_I instructions
# N_R^F Functional Units
# E_R \subset N_I \cross N_R^F
# (j,k) \in E_R means operation j can be executed by functional unit k

### Operations ###
# N(j) where j \in N_I is the interval that j can be executed in
# N(j) = [asap(j) .... alap(j)]
# Q_I^K is the amount of time to execute operation i in function unit K
# L_I^K is the latency (reciperocal throughput according to agner)
# R_K is the number of instances of functional unit k


import pulp # for ILP



class OasicScheduler:
    def __init__(self, prog, uarch):
        # Program
        self._n_i      = prog.get_n_i()
        self._E_d_true = prog.get_E_d_true()
        self._N        = prog.get_N()
        self._M_steps  = prog.get_M_steps()
        # Machine
        self._n_r_f    = uarch.get_n_r_f()
        self._R        = uarch.get_R()
        self._e_r      = uarch.get_e_r(self._n_i)
        self._Q_k_i    = uarch.get_Q_k_i(self._n_i)

    def schedule(self,verbose=False):
        #########################
        # Decision Variable (x) #
        #########################
        # x_{j,n}^k \in {0,1}
        # j is the operation
        # k is the functional unit
        # n is the time step
        #decision_variable = [tuple((j,n,k)) for j in n_i for k in n_r_f for n in N[j] ] # do we restrict the time intervals?
        decision_variable = [tuple((j,n,k)) for j in self._n_i for k in self._n_r_f for n in range(1,self._M_steps+1) ]

        if verbose:
            for c in decision_variable:
                print( "x_"+str(c) )

        # turn the variables into ILP vars
        x = pulp.LpVariable.dicts( 'decision_variable',
                                   decision_variable,
                                   lowBound = 0,
                                   upBound = 1,
                                   cat = pulp.LpInteger )

        # now we create the model for the assignment constraint

        oasic_model = pulp.LpProblem( "oasic scheduling model",
                                      pulp.LpMinimize )
        #########################
        # Assignment Constraint #
        #########################
        # The assignment constraint:
        # an operation can only happen once across all time steps and
        # functional units
        for j in self._n_i:
            oasic_model += sum(x[(j,n,k)] for k in self._n_r_f for n in self._N[j] if (j,k) in self._e_r ) == 1

        if verbose:
            print( "Constraints: " + str(oasic_model))


        #########################
        ## Resource Constraint ##
        #########################
        # NOTE: I'm going to ignore reciprical throughput for now: L_I^K
        #       This adds an additional sum to cover the interval where
        #       the functional unit is recovering
        for k in self._n_r_f:
            for n in range(1,self._M_steps+1):
                oasic_model += sum(x[(j,n,k)] for j in self._n_i if (j,k) in self._e_r) <= self._R[k]

        ############################
        ## Dependence Constraints ##
        ############################
        # Need a Dependency Graph (i,j,r) \in E_d^t
        # need latency Q_i^k
        #
        # (i,j) j depends on i
        #
        #  "i" --> "j"
        #  "j" --> "k"
        #  "i" --> "k"

        ################################################
        # These Constraints preserve instruction order #
        ################################################
        for (i,j,r) in self._E_d_true:
            for (nn_i,nn_j) in [(nn_i,nn_j) for nn_i in self._N[i] for nn_j in self._N[j] if nn_j <= nn_i + max([self._Q_k_i[(kk,ii)] for (kk,ii) in self._Q_k_i.keys() if ii == i]) ]:
                oasic_model += sum(x[i,nn_i,k] for k in [kk for (ii,kk) in self._e_r if ii == i] if (k,i) in  self._Q_k_i.keys() and  self._Q_k_i[(k,i)]>=nn_j-nn_i+1) + sum(x[j,nn_j,k] for k in [kk for (ii,kk) in self._e_r if ii == j]) <= 1


        if verbose:
            print( "Constraints: " + str(oasic_model))

        oasic_model.solve()
        print( "The chosen solution is:")
        #for k in x.keys():
        #    print( str(x[k]) +"="+ str(x[k].value()) )

        # time step
        for n in range(1,self._M_steps+1):
            # resource
            for k in self._n_r_f:
                # instruction
                for j in self._n_i:
                    if (j,n,k) in x.keys():
                        if x[(j,n,k)].value() == 1:
                            print( x[(j,n,k)] )


        # time step
        head = "n"
        for r in self._n_r_f:
            head +=  " | " + r
        print( head )
        for n in range(1,self._M_steps+1):
            line = str(n) + ": "
            # resource
            for k in self._n_r_f:
                is_occupied = False
                # instruction
                for j in self._n_i:
                    if (j,n,k) in x.keys():
                        is_occupied = is_occupied or  (x[(j,n,k)].value() == 1)
                if is_occupied:
                    line += "  X   "
                else:
                    line += "  .   "
            print( line )


class AbstractMicroarchitecture:
    def __init__(self):
        print("Implement Me.")
        return;

    # This is a list of available functional units
    # on our architecture
    #
    # Ex: FMA, ALU0, ALU1 ...
    def get_n_r_f(self):
        print("Implement Me.")
        return

    # This is the number of functional units of
    # a given type.
    #
    # Ex: if FMA can take two instructions per
    #     cycle then R[FMA]=2
    def get_R(self):
        print("Implement Me.")
        return

    # e_r is a mapping between instruction types
    # and the functional units that they can use
    #
    # Ex. ADD can go to ALU0 *OR* ALU1
    #
    #   [(ADD, ALU0), (ADD,ALU1) ... ]
    def get_e_r(self,program):
        print("Implement Me.")
        return

    # These are the latencies of instruction i
    # on functional unit k
    #
    # Ex: ADD on unit ALU0 is 4 cycles
    #     ("ALU0",ADD) = 4
    def get_Q_k_i(self,program):
        print("Implement Me.")
        return

################
# Test Example #
################



######################
# Input Architecture #
######################
class ExampleMicroarchitecture(AbstractMicroarchitecture):
    def __init__(self):
        # Note: these lists really should be sets
        self.n_r_f = ["ALU","MUL"]

        # How many of these units do we have?
        self.R = dict()
        self.R["ALU"] = 1
        self.R["MUL"] = 1

        # TODO: Generate this list
        # if type(ins) == math then add (ins, ALU)
        #self.e_r = [("i","ALU"), ("j","ALU"), ("k","MUL")]
        self.e_r = [("i","ALU"), ("j","MUL"), ("j","ALU"), ("k","MUL")]

        # TODO: Generate this from program
        # Machine Instruction Latency
        self.Q_k_i = dict()
        self.Q_k_i[("ALU","i")] = 2
        self.Q_k_i[("ALU","j")] = 1
        self.Q_k_i[("MUL","j")] = 1
        self.Q_k_i[("MUL","k")] = 1

        return

    # This is a list of available functional units
    # on our architecture
    #
    # Ex: FMA, ALU0, ALU1 ...
    def get_n_r_f(self):
        return self.n_r_f

    # This is the number of functional units of
    # a given type.
    #
    # Ex: if FMA can take two instructions per
    #     cycle then R[FMA]=2
    def get_R(self):
        return self.R

    # e_r is a mapping between instruction types
    # and the functional units that they can use
    #
    # Ex. ADD can go to ALU0 *OR* ALU1
    #
    #   [(ADD, ALU0), (ADD,ALU1) ... ]
    def get_e_r(self,program):
        return self.e_r

    # These are the latencies of instruction i
    # on functional unit k
    #
    # Ex: ADD on unit ALU0 is 4 cycles
    #     ("ALU0",ADD) = 4
    def get_Q_k_i(self,program):
        return self.Q_k_i

class SimpleMicroarchitecture(AbstractMicroarchitecture):
    def __init__(self):
        # Note: these lists really should be sets
        self.n_r_f = ["MM0","MM1","AL0","AL1"]

        # How many of these units do we have?
        self.R = dict()
        self.R["AL0"] = 1
        self.R["AL1"] = 1
        self.R["MM0"] = 1
        self.R["MM1"] = 1

        # Mapping instructions to functional unit
        self.ins_map = dict()
        self.ins_map["LD"]  = ["MM1","MM0"]
        self.ins_map["ADD"] = ["AL0","AL1"]
        self.ins_map["MUL"] = ["AL0","AL1"]

        # instruction latencies
        self.lat_map = dict()
        self.lat_map["LD"]  = 1
        self.lat_map["ADD"] = 1
        self.lat_map["MUL"] = 1

        return

    # This is a list of available functional units
    # on our architecture
    #
    # Ex: FMA, ALU0, ALU1 ...
    def get_n_r_f(self):
        return self.n_r_f

    # This is the number of functional units of
    # a given type.
    #
    # Ex: if FMA can take two instructions per
    #     cycle then R[FMA]=2
    def get_R(self):
        return self.R

    # e_r is a mapping between instruction types
    # and the functional units that they can use
    #
    # Ex. ADD can go to ALU0 *OR* ALU1
    #
    #   [(ADD, ALU0), (ADD,ALU1) ... ]
    def get_e_r(self,prog):
        l = [[( (i,out,inp)  ,unit) for unit in self.ins_map[i]] for (i,out,inp) in prog]
        rr = [r for rr in l for r in rr ] # list flattening
        return rr


    # These are the latencies of instruction i
    # on functional unit k
    #
    # Ex: ADD on unit ALU0 is 4 cycles
    #     ("ALU0",ADD) = 4
    def get_Q_k_i(self,prog):
        e_r = self.get_e_r(prog)
        Q_k_i = dict([ ( (unit,(op,out,inp) ), self.lat_map[op])  for ((op,out,inp), unit) in e_r ])
        return Q_k_i


class AbstractProgram:
    def __init__(self):
        print("Implement Me.")
        return

    def get_n_i(self):
        print("Implement Me.")
        return

    def get_E_d_true(self):
        print("Implement Me.")
        return

    def get_M_steps(self):
        print("Implement Me.")
        return

    def get_N(self):
        print("Implement Me.")
        return


#################
# Input Program #
#################

class ExampleProgram(AbstractProgram):
    def __init__(self):
        # list of instructions
        self.n_i   = ["i","j","k"] # N_I

        # Instruction dependencies
        self.E_d_true = [("i","j","var_a"),("j","k","var_b"),("i","k","var_c")]
        #self.E_d_true = [("j","k","var_b"),("i","k","var_c")]

        self.M_steps = 4 # interval

        # This is the valid interval for the instructions
        self.N = dict()
        #N["i"]=range(1,4)
        #N["j"]=range(2,5)
        self.N["i"]=range(1,5)
        self.N["j"]=range(1,5)
        self.N["k"]=range(1,5)

    def get_n_i(self):
        return self.n_i

    def get_E_d_true(self):
        return self.E_d_true

    def get_M_steps(self):
        return self.M_steps

    def get_N(self):
        return self.N


class SimpleProgram(AbstractProgram):
    def __init__(self,prog,interval):
        self.M_steps = interval
        # list of instructions
        self.n_i   = prog

        outputs = dict( [ (outs,(i,outs,ins)) for (i,outs,ins) in prog ] )

        # Instruction dependencies
        l =[ [ (outputs[inp], (i,outs,ins), inp) for inp in filter(lambda x: x in outputs.keys(), ins)] for (i,outs,ins) in prog]
        rr = [r for rr in l for r in rr ] # list flattening
        self.E_d_true = rr

        # This is the valid interval for the instructions
        self.N = dict( [(i,range(1,interval)) for i in prog] )

    def get_n_i(self):
        return self.n_i

    def get_E_d_true(self):
        return self.E_d_true

    def get_M_steps(self):
        return self.M_steps

    def get_N(self):
        return self.N


