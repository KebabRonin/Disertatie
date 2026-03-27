
// python runExperiment.py -path ~/Documents/fac/GECCO_Robot_Body/Framsticks54  -sim "eval-allcriteria.sim;deterministic.sim;recording-body-coords.sim" -opt distance -initialgenotype "X" -generations 10 -genformat 1 -hof_savefile adaptmutf4.gen -pmut 0.8

let complex_format = {
    "data->bodyrecording": [
        [
            9.914827561648437,
            9.806949739857325,
            -0.009999999999999997
        ],
        // ... 1000 simulation steps (= lifespan)
        // As far as I can tell, the simulation is deterministic (the same genotype has the same fitness for COGpath)
        // Of course it is, you're including `deterministic.sim` as an experiment parameter.
        [
            15.929515847942715,
            7.672783577717705,
            -0.004711850403835262
        ]
    ],
    "fit_stdev": 0.0,
    "vertvel": 2.9015812020731684e-05,
    "fit": 0.0008288782134334943,
    "lifespan": 10000.0, // Constant
    "instances": 1, // How many genotypes are spawned in the simulation; Always 1
    /* Fitness */
    "time": 0.024157047271728516,
    "vertpos": -0.008443726578661558,
    "velocity": 0.0008288782134334943,
    "distance": 8.288782134334943,
    "COGpath": np.float64(6.382097488556056),
    /* Data about genotype */
    "numparts": 3,
    "numjoints": 2,
    "numneurons": 2,
    "numconnections": 1,
    "genotype": "(qLcX[|,1:1](, X[Gpart]))",
};