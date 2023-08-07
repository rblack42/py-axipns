from FreeStream import InitialConditions
from Grid import CreateGrid
from AxiSolver import ConicalSolution
from AxiSolver import GenerateMarchingSolution
class app(object):

	def __init__(self):
		CreateGrid()
		InitialConditions()
		GenerateConicalSolution()
		GenerateMarchingSolution()
