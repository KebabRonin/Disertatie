"""
Genman:
 * genoper_f0 "Operators for f0" type="d 0 0 ~Default" flags=65 group=1 help=""
 * genoper_f1 "Operators for f1" type="d 0 0 ~Default" flags=65 group=1 help=""

 neuadd_* ....
The selection params shouldn't be used, since the mutation/selection/xover are handled as part of the competition submission:
------------------- Group #1: Experiment: Parameters: Selection -------------------
 * p_nop "Unchanged" type="f 0 100 20" flags=192 group=1 help=""
 * p_mut "Mutated" type="f 0 100 64" flags=192 group=1 help=""
 * p_xov "Crossed over" type="f 0 100 16" flags=192 group=1 help=""
 * xov_mins "Minimal similarity" type="f 0 9999 0" flags=192 group=1 help="Only genotypes with dissimilarity below this threshold will be crossed over.
Value of 0 means no crossover restrictions."
 * selrule "Selection rule" type="d 0 5 3 ~Random~Fitness-proportional (roulette)~Tournament (2 genotypes)~Tournament (3 genotypes)~Tournament (4 genotypes)~Tournament (5 genotypes)" flags=192 group=1 help="Positive selection: how to choose genotypes for cloning/mutation/crossover"
 * delrule "Delete genotypes" type="d 0 2 ~Randomly~Inverse-proportionally to fitness~Only the worst" flags=192 group=1 help="Negative selection: which genotypes should be removed when we need room for new genotypes in the gene pool.
If multiple-criteria NSGA-II is set as positive selection, this setting is ignored and "worst rank and crowding distance" is used as negative selection."

------------------- Group #2: Experiment: Parameters: Fitness -------------------
 * cr_c "Constant" type="f -10000 10000 0" flags=192 group=2 help="Constant value added to total fitness"
 * cr_life "Life span" type="f -10000 10000 0" flags=192 group=2 help="Weight of life span in total fitness"
 * cr_v "Velocity" type="f -10000 10000 0" flags=192 group=2 help="Weight of horizontal velocity in total fitness"
 * cr_gl "Body parts" type="f -10000 10000 0" flags=192 group=2 help="Weight of body size (number of parts) in total fitness"
 * cr_joints "Body joints" type="f -10000 10000 0" flags=192 group=2 help="Weight of structure size (number of joints) in total fitness"
 * cr_nnsiz "Brain neurons" type="f -10000 10000 0" flags=192 group=2 help="Weight of brain size (number of neurons) in total fitness"
 * cr_nncon "Brain connections" type="f -10000 10000 0" flags=192 group=2 help="Weight of brain connections in total fitness"
 * cr_di "Distance" type="f -10000 10000 0" flags=192 group=2 help="Weight of distance in total fitness"
 * cr_vpos "Vertical position" type="f -10000 10000 0" flags=192 group=2 help="Weight of vertical position in total fitness"
 * cr_vvel "Vertical velocity" type="f -10000 10000 0" flags=192 group=2 help="Weight of vertical velocity in total fitness"
 * cr_norm "Criteria normalization" type="d 0 1 0" flags=192 group=2 help="Normalize each criterion to 0..1 interval before weighting"
 * cr_simi "Similarity speciation" type="d 0 1 0" flags=192 group=2 help="If enabled, fitness of each genotype will be reduced by its phenotypic similarity to all other genotypes in the gene pool"
 * cr_nsga "NSGA-II for multiple criteria" type="d 0 1 0" flags=192 group=2 help="If enabled, fitness will be replaced with Pareto ranks from NSGA-II (Non-dominated Sorting Genetic Algorithm) method.
Using tournament selection is recommended.
This setting also forces negative selection to be "worst rank and crowding distance" independently from the negative selection setting."
"""

"""
------------------- Group #3: Genetics: f0 -------------------
 * f0_nodel_tag "Respect the 'delete inhibit' tag" type="d 0 1 1" flags=0 group=3 help="You can tag elements using their 'i' field and the i="mi=d" tag.
Mutations will not delete such elements.
The i="mi=dm" combination is allowed."
 * f0_nomod_tag "Respect the 'modify inhibit' tag" type="d 0 1 1" flags=0 group=3 help="You can tag elements using their 'i' field and the i="mi=m" tag.
Mutations will not modify properties of such elements.
The i="mi=md" combination is allowed."

------------------- Group #4: Genetics: f0: Parts -------------------
 * f0_p_new "New part" type="f 0 100 4" flags=0 group=4 help=""
 * f0_p_del "Delete part" type="f 0 100 4" flags=0 group=4 help=""
 * f0_p_swp "Swap parts" type="f 0 100 1" flags=0 group=4 help=""
 * f0_p_pos "Position" type="f 0 100 4" flags=0 group=4 help=""
 * f0_p_den "Density" type="f 0 100 0" flags=0 group=4 help="Density only has an influence under water"
 * f0_p_frc "Friction" type="f 0 100 1" flags=0 group=4 help=""
 * f0_p_ing "Ingestion" type="f 0 100 0" flags=0 group=4 help=""
 * f0_p_asm "Assimilation" type="f 0 100 0" flags=0 group=4 help="The interpretation and influence of this property must be implemented by the experiment definition"
 * f0_p_color "Visual only: color" type="f 0 100 0.01" flags=0 group=4 help="If this value is above zero, apart from this mutation occurring, the color of every newly created gray Part will be mutated on creation"

------------------- Group #5: Genetics: f0: Joints -------------------
 * f0_j_new "New joint" type="f 0 100 4" flags=0 group=5 help=""
 * f0_j_del "Delete joint" type="f 0 100 1" flags=0 group=5 help=""
 * f0_j_stm "Stamina" type="f 0 100 0" flags=0 group=5 help="The interpretation and influence of this property must be implemented by the experiment definition"
 * f0_j_stf "Stiffness" type="f 0 100 0" flags=0 group=5 help=""
 * f0_j_rsf "Rotational stiffness" type="f 0 100 0" flags=0 group=5 help=""
 * f0_j_color "Visual only: color" type="f 0 100 0.01" flags=0 group=5 help="If this value is above zero, apart from this mutation occurring, every newly created Joint will be assigned a color that is the average color of both joined Parts"

------------------- Group #6: Genetics: f0: Neurons -------------------
 * f0_n_new "New neuron" type="f 0 100 3" flags=0 group=6 help=""
 * f0_n_del "Delete neuron" type="f 0 100 3" flags=0 group=6 help=""
 * f0_n_prp "Change properties" type="f 0 100 1" flags=0 group=6 help=""

------------------- Group #7: Genetics: f0: Connections -------------------
 * f0_c_new "New connection" type="f 0 100 2" flags=0 group=7 help=""
 * f0_c_del "Delete connection" type="f 0 100 2" flags=0 group=7 help=""
 * f0_c_wei "Change weight" type="f 0 100 1" flags=0 group=7 help=""
"""
"""
------------------- Group #13: Genetics: f1 -------------------
 * f1_xo_propor "Proportional crossover" type="d 0 1 1" flags=0 group=13 help="Cross over (exchange) corresponding segments of the two parent genotypes?

f1 uses a two-point crossing over.
If this option is turned on, cut points will be selected proportionally to neural genes in both parents, and a similar number of characters will be exchanged if possible.
Thus, if both parents have the same number of neurons, then this will be preserved in their children."

------------------- Group #14: Genetics: f1: Morphology -------------------
 * f1_smX "Add/remove a stick X" type="f 0 100 4" flags=0 group=14 help=""
 * f1_smJunct "Add/remove a branch ( )" type="f 0 100 1" flags=0 group=14 help=""
 * f1_smComma "Add/remove a comma ," type="f 0 100 1" flags=0 group=14 help=""
 * f1_smModif "Add/remove a modifier" type="f 0 100 4" flags=0 group=14 help="Modifiers: LlRrCcQqFfMmEeWwSsAaIiDdGgBb"
 * f1_smModifiers "Allowed modifiers" type="s 0 100" flags=0 group=14 help="Modifier symbols that will be added or deleted during mutation
(from the full set: LlRrCcQqFfMmEeWwSsAaIiDdGgBb).

You may use the extended syntax: after every allowed symbol, you may include its probability value in parentheses.
Without parentheses, all allowed symbols behave as if they had (1.0) appended.
If you include (0.0) after a symbol, this bans that symbol as if it was not present in this string."

------------------- Group #15: Genetics: f1: Neuron net -------------------
 * f1_nmNeu "Add/remove a neuron" type="f 0 100 4" flags=0 group=15 help="Adds a (connected) neuron or removes a neuron"
 * f1_nmConn "Add/remove neural connection" type="f 0 100 2" flags=0 group=15 help=""
 * f1_nmProp "Add/remove neuron property setting" type="f 0 100 1" flags=0 group=15 help=""
 * f1_nmWei "Change connection weight" type="f 0 100 1" flags=0 group=15 help=""
 * f1_nmVal "Change property value" type="f 0 100 1" flags=0 group=15 help=""
"""
# These values are taken from eval-allcriteria.sim, but it would be better to load them on Framsticks initialization.
BODY_MUT = {
  "0":  {
# Mutation weights pertaining to body parts/joints,
    "f0_p_new": 5.0,
    "f0_p_del": 5.0,
    "f0_p_swp": 10.0,
    "f0_p_pos": 10.0,
    "f0_p_den": 0.0,
    "f0_p_frc": 10.0,
    "f0_p_ing": 10.0,
    "f0_p_asm": 0.0,
    "f0_p_color": 0.0,
    "f0_j_new": 5.0,
    "f0_j_del": 5.0,
    "f0_j_stm": 0.0,
    "f0_j_stf": 10.0,
    "f0_j_rsf": 10.0,
    "f0_j_color": 0.0,
  },
  "1":  {
    # "f1_smModifiers": "LlRrCcQqFfMm",
    "f1_smX": 0.05,
    "f1_smJunct": 0.02,
    "f1_smComma": 0.02,
    "f1_smModif": 0.1,
  },
}

NEURO_MUT = {
  "0":  {
# ??? Idk how to add tags,
    "f0_nodel_tag": 1,
    "f0_nomod_tag": 1,
# Mutation weights pertaining to neurons/neuron connections,
    "f0_n_new": 5.0,
    "f0_n_del": 5.0,
    "f0_n_prp": 10.0,
    "f0_c_new": 5.0,
    "f0_c_del": 5.0,
    "f0_c_wei": 10.0,
  },
  "1":  {
# f1 only: Available gene modifiers
    "f1_xo_propor": 1, # point crossover will cut so the same amount of neurons is in both cut parts
    "f1_nmNeu": 0.05,
    "f1_nmConn": 0.1,
    "f1_nmProp": 0.1,
    "f1_nmWei": 1.0,
    "f1_nmVal": 0.05,
  },
  "generic": {
# Which kinds of neurons to generate.
    "neuadd_N": 1,
    "neuadd_Nu": 0,
    "neuadd_G": 1,
    "neuadd_Gpart": 1,
    "neuadd_T": 1,
    "neuadd_Tcontact": 0,
    "neuadd_Tproximity": 0,
    "neuadd_S": 1,
    "neuadd_Constant": 1,
    "neuadd_Bend_muscle": 1,
    "neuadd_Rotation_muscle": 1,
    "neuadd_M": 1,
    "neuadd_D": 0,
    "neuadd_Fuzzy": 0,
    "neuadd_VEye": 0,
    "neuadd_VMotor": 0,
    "neuadd_Sti": 0,
    "neuadd_LMu": 0,
    "neuadd_Water": 0,
    "neuadd_Energy": 0,
    "neuadd_Ch": 0,
    "neuadd_ChMux": 0,
    "neuadd_ChSel": 0,
    "neuadd_Rnd": 0,
    "neuadd_Sin": 0,
    "neuadd_Delay": 0,
    "neuadd_Light": 0,
    "neuadd_Nn": 0,
    "neuadd_PIDP": 0,
    "neuadd_PIDV": 0,
    "neuadd_SeeLight": 0,
    "neuadd_SeeLight2": 0,
    "neuadd_S0": 0,
    "neuadd_S1": 0,
    "neuadd_Thr": 0,
  }
}

# TBD What parameter groups are useful to take together.
SHORTCUTS = {
  'add_thing': [
    'f0_n_new', 'f0_c_new',
    'f1_nmNeu', 'f1_nmConn', 'f1_nmProp',
    # ????
  ],
}

INFO_MUT = {
  '0':{
    "added Neuron": "f0_n_new",
    "changed Neuron property": "f0_n_prp",
    "removed Neuron": "f0_n_del",
    "added neural connection": "f0_c_new",
    "changed neural connection weight": "f0_c_wei",
    "removed neural connection": "f0_c_del",
    "added Joint": "f0_j_new",
    "changed Joint color": "f0_j_color",
    "changed Joint stamina": "f0_j_stm",
    "changed Joint stiffness": "f0_j_stf",
    "changed Joint rotational stiffness": "f0_j_rsf",
    "removed Joint": "f0_j_del",
    "added Part": "f0_p_new",
    "changed Part density": "f0_p_den",
    "changed Part ingestion": "f0_p_ing",
    "changed Part friction": "f0_p_frc",
    "changed Part assimilation": "f0_p_asm",
    "changed Part position": "f0_p_pos",
    "changed Part color": "f0_p_color",
    "swapped Part": "f0_p_swp",
    "removed Part": "f0_p_del",
  },
  '1': {
    "added or removed a neuron": "f1_nmNeu",
    "added or removed neuron property": "f1_nmProp",
    "changed neuron property": "f1_nmVal",
    "added or removed neural connection": "f1_nmConn",
    "changed neural connection weight": "f1_nmWei",
    "added or removed a modifier": "f1_smModif",
    "added or removed a comma": "f1_smComma",
    "added or removed X": "f1_smX",
    "added or removed branching": "f1_smJunct",
  }
}
class CmutFramsLibReference:
  custom_mut_frams_lib_reference = None
  ignored_operation_types = list(NEURO_MUT['generic'].keys())

def setExpProperty(name, value):
  # print(CmutFramsLibReference.custom_mut_frams_lib_reference)
  exec(f"frams.GenMan.{name} = {value}", {'frams': CmutFramsLibReference.custom_mut_frams_lib_reference})

def getExpProperty(name):
  # print(CmutFramsLibReference.custom_mut_frams_lib_reference)
  rval = eval(f"frams.GenMan.{name}._value()", globals={'frams': CmutFramsLibReference.custom_mut_frams_lib_reference})
  return rval

def set_general_weights(framsLib, w_body=None, w_neuro=None):
  """
  In case you want to set some weight to a more general class of mutation operators. 
  """
  pass

def get_all_prop_names(genetic_repr = None):
    #list(NEURO_MUT["generic"].keys()) + 
  names = list(NEURO_MUT["0"].keys() if genetic_repr != '1' else []) + list(NEURO_MUT["1"].keys() if genetic_repr != '0' else []) + \
    list(BODY_MUT["0"].keys() if genetic_repr != '1' else []) + list(BODY_MUT["1"].keys() if genetic_repr != '0' else [])
  return list(set(filter(lambda x: x not in CmutFramsLibReference.ignored_operation_types, names)))

def get_current_weights(framsLib, genetic_repr):
  d = {}
  for prop in get_all_prop_names():
    d[prop] = getExpProperty(prop)
  return d

def normalize_weights(framsLib, genetic_repr, settings=None):
  """
  Normalize mutation weights, so they sum up to 1. This is already done by framsticks, so this method is probably useless.
  """
  if settings is None:
    return
  for s in settings.keys():
    setExpProperty(s, settings[s])


import re
MUTATION_INFO_RE = re.compile(r'mutation\((.*?)\)')
def get_applied_mutation(offspring) -> str:
  """
  Get the type of mutation that was last applied to this genotype.
  Requires frams.GenMan.gen_extmutinfo = 2 to be set.
  """
  assert getExpProperty('gen_extmutinfo') == 2, getExpProperty('gen_extmutinfo')
  s = str(offspring.info)
  m = re.search(MUTATION_INFO_RE, s)
  if not m:
    if not re.search('Crossing over of ', s):
      print('Unknown operation type:', s, 'ooo')
      # exit(-1)
      return 'invalid'
    return 'crossover'
  mutation_match = m.group(1)
  if mutation_match not in INFO_MUT[offspring.format._value()]:
    print('Unknown mutation type:', mutation_match, 'eee')
    return 'invalid'
    # exit(-1)
  return INFO_MUT[offspring.format._value()][mutation_match]