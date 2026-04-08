import sys, os

P_SIZE = 100

runs = [
    #f'''python run_more.py -runname convectionEaSimpleF0pop{P_SIZE} -commandargs "-genformat 0 -algorithm convection_eaSimple -popsize {P_SIZE}"''',
    ##f'''python run_more.py -runname convectionEaSimpleF1pop{P_SIZE} -commandargs "-genformat 1 -algorithm convection_eaSimple -popsize {P_SIZE}"''',
    f'''python run_more.py -runname convectionEaSimpleF1pmut08pop{P_SIZE} -commandargs "-genformat 1 -algorithm convection_eaSimple -pmut 0.8 -popsize {P_SIZE}"''',
    #f'''python run_more.py -runname eaSimpleF0pop{P_SIZE} -commandargs "-genformat 0 -algorithm eaSimple -popsize {P_SIZE}"''',
    #f'''python run_more.py -runname eaSimpleF1pop{P_SIZE} -commandargs "-genformat 1 -algorithm eaSimple -popsize {P_SIZE}"''',
    #f'''python run_more.py -runname convectionAdaptMutF0pop{P_SIZE} -commandargs "-genformat 0 -algorithm convection_AdaptMut -popsize {P_SIZE}"''',
    #f'''python run_more.py -runname convectionAdaptMutF1pop{P_SIZE} -commandargs "-genformat 1 -algorithm convection_AdaptMut -popsize {P_SIZE}"''',
    #f'''python run_more.py -runname convectionAdaptMutF1pmut08pop{P_SIZE} -commandargs "-genformat 1 -algorithm convection_AdaptMut -pmut 0.8 -popsize {P_SIZE}"''',
    #f'''python run_more.py -runname adaptMutF0pop{P_SIZE} -commandargs "-genformat 0 -algorithm AdaptMut -popsize {P_SIZE}"''',
    #f'''python run_more.py -runname adaptMutF1pop{P_SIZE} -commandargs "-genformat 1 -algorithm AdaptMut -popsize {P_SIZE}"''',
    ##f'''python run_more.py -runname adaptMutF0pmut08pop{P_SIZE} -commandargs "-genformat 0 -algorithm AdaptMut -pmut 0.8 -popsize {P_SIZE}"''',
    #f'''python run_more.py -runname adaptMutF1pmut08pop{P_SIZE} -commandargs "-genformat 1 -algorithm AdaptMut -pmut 0.8 -popsize {P_SIZE}"''',
]

print(f"We'll be back in {len(runs) * 8} h ({len(runs) * 8 / 24:.2f} days)")

os.system(' && '.join(runs))