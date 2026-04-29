
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
    "f1_smModifiers": "LlRrCcQqFfMm",
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
    "f1_nmProp": 0.1, # ??
    "f1_nmWei": 1.0, # ??
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

DEFAULTS = {

}

def set_general_weights(framsLib, w_body, w_neuro):
  pass

def get_current_weights(framsLib, genetic_repr):
  pass
  return {}

def set_weights(framsLib, genetic_repr, settings=DEFAULTS):
  pass
  for s in settings.keys():
    exec(f"frams.GenMan.{s} = {settings[s]}")