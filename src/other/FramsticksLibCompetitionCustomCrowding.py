from framspy.FramsticksLibCompetition import FramsticksLibCompetition
import numpy as np

class FramsticksLibCompetitionCustomCrowding(FramsticksLibCompetition):
	"""
	Custom wrapper which adds a custom Crowding fitness measure.
	"""

	def __init__(self, frams_path, frams_lib_name, sim_settings_files, dissimMethod, toolbox):
		super().__init__(frams_path, frams_lib_name, sim_settings_files)
		self.dissimMethod = dissimMethod
		self.toolbox = toolbox
		# These will be injected by the algorithm when necessary, in order to not recompute the distance matrix popsize times
		# when evaluating.
		self.distanceMatrix = None

	def getGenoIdx(self, geno):
		return self.genoIdxMap[geno[0]]

	def get_dissimMatrix(self, genotype_list):
		if self.distanceMatrix is None:
			self.distanceMatrix = self.toolbox.dissimilarity(genotype_list, self.dissimMethod)
			self.genoIdxMap = {x[0]: idx  for idx, x in enumerate(genotype_list)}
		return self.distanceMatrix

	def _evaluate_single_genotype(self, genotype):
		ret = super()._evaluate_single_genotype(genotype)
		if ret[0]['evaluations'] == None:
				pass
		else:
				# Add the crowding distance as an evaluated fitness metric, if a dissim method was defined.
				distanceMatrix = self.get_dissimMatrix(self, )
				# TODO: HOW TO GET THE INDEX OF THE GENOTYPE??
				ret[0]['evaluations']['']['crowding'] = np.linalg.norm(self.distanceMatrix[self.getGenoIdx(genotype)], ord=2)
		return ret