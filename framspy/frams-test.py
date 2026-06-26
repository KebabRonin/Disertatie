"""Simple examples of using the "frams" module to communicate directly with the Framsticks library (dll/so).

For an introduction to Framsticks, its usage and scripting, see https://www.youtube.com/playlist?list=PLkPlXm7pOPatTl3_Gecx8ZaCVGeH4UV1L
For a list of available classes, objects, methods and fields, see http://www.framsticks.com/files/classdoc/
For a number of examples of scripting, see the "scripts" directory in the Framsticks distribution."""

import sys
import json
import Disertatie.framspy.frams as frams

frams.init(*(sys.argv[1:]))  # pass whatever args we have, init() is the right place to deal with different scenarios:
# frams.init() - should try to figure out everything (and might fail)
# frams.init('path/to/lib') - load the library from the specified directory and configure Framsticks path as "data" inside this directory
# frams.init('path/to/lib','-d/tmp/workdir/data') - as above, but set the working (writable) directory somewhere else (see also -D)
# frams.init('path/to/lib','-Lframs-objects-alt.dll') - use specified library location and non-default file name

print('Available objects:', dir(frams))
print()


def extValueDetails(v):
	"""A helper function to display basic information about a variable of type ExtValue."""
	return '\t"' + str(v) + '"    frams type=' + str(v._type()) + '    frams class=' + str(v._class()) + '    python type=' + str(type(v._value()))


dic_as_string = '[100,2.2,"abc",[null,[],{}],XYZ[9,8,7]]'
print("We have the following string:\n\t'%s'" % dic_as_string)
print("Looks like a serialized dictionary, let's ask Framsticks String.deserialize() to do its job.")
v = frams.String.deserialize(dic_as_string)
print("Framsticks String.deserialize() returned\n\t", type(v))
print("More specifically, it is:")
print(extValueDetails(v))
print("Even though it is ExtValue (Framsticks' Vector), it supports iteration like a python vector, so let's inspect its elements:")
for e in v:
	print(extValueDetails(e))

print("\nNow let's play with the Framsticks simulator. Let's create a Genotype object and set fields in its custom 'data' dictionary.")
g = frams.GenePools[0].add('X')
g.name = "Snakis Py"
g.data['custom'] = 123.456
g.data['a'] = 'b'  # implicit conversion, looks like python dictionary but still converts '3' and '4' to ExtValue
dic = frams.Dictionary.new()  # let's create a Dictionary object from Framsticks
dic.set('1', '2')  # calling set() from Framsticks Dictionary
dic['3'] = '4'  # implicit conversion, looks like python dictionary but still converts '3' and '4' to ExtValue
g.data['d'] = dic
print(extValueDetails(g))

print("Let's add a few mutants and display their data:")
for more in range(5):
	frams.GenePools[0].add(frams.GenMan.mutate(g.geno))

for g in frams.GenePools[0]:
	print("\t%d. name='%s'\tgenotype='%s'\tdata=%s" % (g.index._value(), str(g.name), str(g.genotype), str(g.data)))

print("Let's now change some property of the simulation. Current water level is", frams.World.wrldwat)
frams.World.wrldwat = 0.5
print("Now water level is", frams.World.wrldwat)
frams.World.wrldwat = frams.World.wrldwat._value() + 0.7
print("Now water level is", frams.World.wrldwat)

initial_genotype = r"""//0
p:0.214, 0.079, 0.16, fr=1.322, ing=0.326
p:0.412, -0.163, 0.389, fr=0.685, ing=0.083
p:-1.473, 0.332, -1.2, fr=0.03, ing=0.542
p:-1.2959165401353254, 0.4781397688300989, -1.0890154229488218, fr=0.005, ing=0.201
p:-0.4297716999554018, 1.342551954009019, -0.6228961206239585, fr=2.206, ing=0.2
p:1.8293315372452914, 1.2424433827758363, 0.3505349308024196, fr=1.218, ing=0.064
p:1.8, 1.539, 0.97, fr=0.053, ing=0.298
p:2.69, 0.519, 0.026, fr=0.409, ing=0.003
j:0, 5, stif=0.755, rotstif=0.843
j:3, 0, stif=0.927, rotstif=0.49
j:0, 1, stif=0.985, rotstif=0.856
j:5, 1, stif=0.918, rotstif=0.906
j:4, 1, stif=0.923, rotstif=0.839
j:2, 3, stif=0.985, rotstif=0.948
j:0, 4, stif=0.812, rotstif=0.994
j:6, 5, stif=0.836, rotstif=0.947
j:7, 5, stif=0.582, rotstif=0.997
n:j=0, d="|:p=0.338, r=0.984"
n:j=0, d=G
n:j=3, d="|:p=0.384, r=0.961"
n:j=3, d=G
n:d="N:in=0.889, si=0.616"
n:d=*
n:d="N:fo=0.647, si=4.233"
n:d=*
n:p=4, d=Gpart
n:p=2, d=Gpart:rz=-0.061
n:p=0, d="T:r=0.873, rz=-1.412"
n:j=1, d=G
c:2, 5, 1.451
c:6, 10, 2.322
c:6, 11, -2.376"""
initial_genotype = """MXX[*][S][N, 10:-7.496, 10:3.812, 0:2.899, 0:0.527, 0:-21.133, 0:16.436, 0:-3.347, 1:-13.831, -1:10.714, 4:-4.933, 4:1.753, 0:0.761,8:1][Gpart, rz:3.991, ry:2.984]qfMXfFX[Gpart][T][N, -4:0.95, -3:-2.129, -5:-4.18, -4:4.344, -2:2.306, -3:1.398,-6:-4.825,0:1]RLMfc(, QFMX[|, 5:28.963][@, 4:-36.341]MF(, qX[T]M(MlX[S][@, -8:1.232, p:0.816][Gpart,ry:0])))"""  # simple body with touch and gyroscope sensors
initial_genotype = """/*4*/X"""

# print(frams.Model.newFromString(initial_genotype))
# print(frams.Model.newFromString(initial_genotype))

# exit(0)

print("Let's perform a few simulation steps of the initial genotype:", initial_genotype)
frams.ExpProperties.initialgen = initial_genotype
frams.ExpProperties.p_mut = 0  # no mutation (the selection procedure will clone our initial genotype)
frams.ExpProperties.p_xov = 0  # no crossover (the selection procedure will clone our initial genotype)
frams.Populations[0].initial_nn_active = 1  # immediate simulation of neural network - no "waiting for stabilization" period
frams.World.wrldg = 5  # gravity=5x default, let it fall quickly

frams.Simulator.init()  # adds initial_genotype to gene pool (calls onInit() from standard.expdef)
frams.Simulator.start()  # this does not actually start the simulation, just sets the "Simulator.running" status variable
step = frams.Simulator.step  # cache reference to avoid repeated lookup in the loop (just for performance)
# frams.Simulator.eval("while(Simulator.running) Simulator.step();")  # loop in FramScript much faster than loop in python
frams.GenMan.gen_extmutinfo = 2
from ..src.dalgorithm.customMutation import *
CmutFramsLibReference.custom_mut_frams_lib_reference = frams
print(CmutFramsLibReference.custom_mut_frams_lib_reference)
# initial_genotype = """X"""
# print(len(frams.Populations[0]))
# for k in get_all_prop_names():
# 	setExpProperty(k, 0)
# setExpProperty('f0_n_del', 1)
# setExpProperty('f0_p_del', 1)
# d = {}
# for s in range(3000):
# 	step()  # first step performs selection and revives one genotype according to standard.expdef rules
# 	# creature = frams.Populations[0][0]  # FramScript Creature object
# 	offspring = frams.GenMan.mutate(frams.Geno.newFromString(initial_genotype))
# 	# print(offspring.genotype)
# 	d[offspring.genotype._value()] = 1 + d.setdefault(offspring.genotype._value(), 0)
# print('oops')
# for k in d:
# 	print(d[k], k)
# exit(0)
parent = frams.Geno.newFromString(initial_genotype)
child = frams.GenMan.mutate(parent)

print("child.info type:", type(child.info))
print("child.info repr:", repr(str(child.info)))
print("child.info text:\n", str(child.info))

for bmut in get_all_prop_names():
	setExpProperty(bmut, 1)
setExpProperty("f4_mut_add", 0)
setExpProperty("f4_mut_del", 0)
d = {}
"""
0
{'added Neuron': 5177, 'changed Joint color': 4915, 'removed neural connection': 5073, 'changed Part density': 5157, 'added neural connection': 5118, 'changed Neuron property': 2995, 'changed Joint stamina': 5212, 'changed Part ingestion': 5255, 'added Joint': 3334, 'changed Joint stiffness': 5076, 'changed neural connection weight': 5069, 'changed Part friction': 5080, 'removed Part': 3159, 'changed Part assimilation': 5186, 'swapped Part': 3880, 'removed Neuron': 5161, 'changed Part color': 5260, 'added Part': 5061, 'removed Joint': 4708, 'changed Part position': 5129, 'changed Joint rotational stiffness': 4995}
1
{'added or removed a neuron': 7033, 'changed neural connection weight': 7009, 'added or removed neural connection': 7034, 'added or removed a modifier': 27813, 'added or removed a comma': 6450, 'added or removed X': 26034, 'added or removed neuron property': 6935, 'changed neuron property': 7040, 'added or removed branching': 4652}
4
"""
import re
initial_genotype = "/*4*/c<<CXR>MfmN:Gpart>fN:@[1:0.788]>"
for s in range(100_000):
	step()  # first step performs selection and revives one genotype according to standard.expdef rules
	# creature = frams.Populations[0][0]  # FramScript Creature object
	offspring = frams.GenMan.mutate(frams.Geno.newFromString(initial_genotype))
	# print(offspring.genotype)
	print(offspring.info)
	# exit(0)
	mutation_match = re.search(r'mutation\((.*?)\)', str(offspring.info)).group(1)
	mutkind = get_applied_mutation(offspring)
	initial_genotype = offspring.genotype._string()
	d[mutkind] = d.get(mutkind, 0) + 1
print(d)
exit(0)
creature_orig = str((frams.Populations[0][0]).genotype)
print('=', creature_orig)
import copy, random
def getrandcreature(creature_orig):
	creature_latest2 = copy.deepcopy(creature_orig)
	for s in range(random.randrange(3,40)):
		creature = frams.Geno.newFromString(creature_latest2)
		# step()  # first step performs selection and revives one genotype according to standard.expdef rules
		offspring = frams.GenMan.mutate(frams.Geno.newFromString(creature.genotype))
		# print(offspring.genotype)
		creature_latest2 = str(offspring.genotype) # Replace
	return creature_latest2

creatures = [creature_orig] + [getrandcreature(creature_orig) for i in range(5)]

from FramsticksLib import FramsticksLib, DissimMethod

print(f"Comparing {creatures}")

def frams_dissim(frams_lib: FramsticksLib, individuals: list, dissim_method:DissimMethod):
	# print(individuals)
	return frams_lib.dissimilarity(individuals, method=dissim_method)
FramsticksLib.DETERMINISTIC = False
fsl = FramsticksLib('../../Framsticks54', None, 'eval-allcriteria.sim;deterministic.sim;recording-body-coords.sim')
violations={dm: {'triangle': 0, 'sim': 0, 'time': 0} for dm in DissimMethod}
import numpy as np, time

def test_distances(violations):
	creatures = [creature_orig] + [getrandcreature(creature_orig) for i in range(5)]
	for dm in DissimMethod:
		if dm == DissimMethod.FITNESS:
			continue
		try:
			t0 = time.perf_counter()
			l = frams_dissim(fsl, creatures, dm)
			violations[dm]['time'] += time.perf_counter() - t0
			# print(dm,'\n', l)
			non_symmetric_diff = l - l.T
			non_symmetric_count = np.any(non_symmetric_diff > DELTA)
			if non_symmetric_count is True:
				violations[dm]['sim'] += 1
			for i in range(5):
				for j in range(i+1, 5):
					for k in range(j+1, 5):
						if l[i][j] - (l[i][k] + l[k][j]) > DELTA: # 1e-15
							violations[dm]['triangle'] += 1
							print("[WARN] DOESN'T RESPECT: ", l[i][j], l[i][k] + l[k][j])
							raise Exception("ha")
		except Exception as e:
			print(e)
			pass
import tqdm
evals = 100
DELTA = 1e-15
[test_distances(violations) for i in tqdm.trange(evals)]
for v in violations:
	print(f"{v:<60} {violations[v]['sim'] / evals:.3f} {violations[v]['triangle'] / evals:.3f}, {violations[v]['time'] / evals}")

exit(0)
frams.Simulator.stop()
# changing expdef
testgenotype = "XrrX[G][-1:80][|,-1:0.9]X[|,-2:-21]"
evaluations = 1
print("\nLet's change the experiment definition (expdef) and evaluate genotype '%s' %d times." % (testgenotype, evaluations))
frams.Simulator.expdef = "standard-eval"
frams.ExpProperties.evalcount = evaluations
frams.ExpProperties.cr_v = 1
frams.ExpProperties.evalplan = ":velocity,vertpos,fit_stdev,time"
frams.GenePools[0].add(testgenotype)
frams.ExpProperties.evalsavefile = ""  # no need to store results in a file - we will get evaluations directly from Genotype's "data" field
frams.Simulator.init()
frams.Simulator.start()
# step = frams.Simulator.step  # cache reference to avoid repeated lookup in the loop (just for performance)
# while frams.Simulator.running._int():  # standard-eval.expdef sets running to 0 when the evaluation is complete
#	step()
frams.Simulator.eval("while(Simulator.running) Simulator.step();")  # loop in FramScript much faster than loop in python
for g in frams.GenePools[0]:  # loop over all genotypes, even though we know we added only one
	serialized_dict = frams.String.serialize(g.data[frams.ExpProperties.evalsavedata._value()])
	print(json.loads(serialized_dict._string()))

# sampling a Model in 3D
geno = "RXX(X,CXXX)"
print("\nNow build a Model from the genotype '%s' and sample it in 3D, then print a 2D projection." % geno)
import numpy as np

matrix = np.zeros((20, 20, 20), dtype=int)  # 3D matrix, "voxels"
m = frams.ModelGeometry.forModel(frams.Model.newFromString(geno))
m.geom_density = 20
for p in m.voxels():
	# print('%f %f %f ' % (p.x._value(), p.y._value(), p.z._value()))
	matrix[int(p.x._value() * 5 + 2), int(p.y._value() * 5 + 5), int(p.z._value() * 5 + 6)] += 1  # scaling and offsets adjusted manually to fit the matrix nicely
matrix = np.sum(matrix, axis=1)  # sum along axis, make 2D from 3D ("projection")
np.set_printoptions(formatter={'int': lambda x: ('.' if x == 0 else str(x // 18))})  # print zeros as dots, x//18 to fit a larger range into a single digit
print(matrix)
np.set_printoptions()  # without this line, due to interaction with numpy and the order of object destruction, finalizers of some ExtValue objects are called AFTER c_api becomes None (when the script finishes, Python 3.12.3), leading to the inability to call extFree() in frams.py, in __del__() - hence that finalizer is now additionally protected against c_api being None.


#
#
# Note that implementing a complete expdef, especially a complex one, entirely in python may be inconvenient or impractical
# because you do not have access to "event handlers" like you have in FramScript - onStep(), onBorn(), onDied(), onCollision() etc.,
# so you would have to check various conditions in python in each simulation step to achieve the same effect.
