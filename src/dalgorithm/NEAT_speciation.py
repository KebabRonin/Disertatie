import random
import numpy as np
import math
from deap import tools

from ..runExperiment import FITNESS_VALUE_INFEASIBLE_SOLUTION

UID_P10 = 10**10
TEST = True

def s_int(x):
    """Stochastic rounding"""
    a = math.floor(x)
    b = a + 1
    return (np.random.choice([a, b], p=[b - x, x - a]))

class Species:
    def __init__(self, pop: list):
        self.pop = pop
        self.past_fitnesses = []
        self.uid = id(self) % UID_P10

    @property
    def age(self):
        return len(self.past_fitnesses)

    def is_stagnant(self, horizon):
        if len(self.past_fitnesses) < horizon:
            return False
        else:
            # If the best past fitness is not greater than the last fitness, then stagnate
            return max(self.past_fitnesses[-horizon:]) < self.past_fitnesses[-1]

    @property
    def species_fitness(self):
        return sum([max(0, ind._fitness[0]) for ind in self.pop])

    def get_representative(self):
        return random.choice(self.pop) if len(self.pop) > 0 else None

    def compute_fitness(self, distance_matrix, admission_delta):
        for idx, ind in enumerate(self.pop):
            distances = [(distance_matrix[i][idx] + distance_matrix[idx][i]) / 2 for i in range(len(self.pop)) if i != idx]
            norm = len(list(filter(lambda x: x <= admission_delta, distances))) + 1 # +1 to avoid division by 0
            # print(ind.fitness.values, norm)
            ind._fitness = [
                (ind.fitness.values[j] / norm) if ind.fitness.values[j] 
                else FITNESS_VALUE_INFEASIBLE_SOLUTION for j in range(len(ind.fitness.values))]
        self.past_fitnesses.append(max([ind.fitness.values[0] for ind in self.pop]))

def assert_nonempty_species(species, name):
    for s in species:
        if len(s.pop) == 0:
            print(f"Species {[len(s.pop) for s in species]} contains zeros <{name}>")
            exit(6)

def assert_unique(pop, name):
    pp = [id(p) for p in pop]
    for p in pop:
        if pp.count(id(p)) != 1:
            print(f"{id(p)} appears {pp.count(id(p))} times <{name}>")
            exit(5)

def remove_empty_species(new_species, name=''):
    to_remove = []
    for i, species in enumerate(new_species):
        if len(species.pop) == 0:
            to_remove.append(i)
    for i in reversed(to_remove):
        # if TEST:
        print(f'Removed species {new_species[i].uid} since it was empty. <{name}>')
        new_species.pop(i)
    return new_species

def split_in_species(previous_species: list[Species], distance_matrix, admission_delta):
    """
    """
    representants = []
    new_species = []
    for i, species in enumerate(previous_species):
        repres = species.get_representative()
        if repres is not None:
            representants.append(repres)
            new_species.append(Species([]))
            # Preserve the histories.
            new_species[-1].past_fitnesses = previous_species[i].past_fitnesses
            new_species[-1].uid = previous_species[i].uid
    pop = []
    for sp in previous_species:
        pop += sp.pop
    assert_unique(pop, 'start of split')
    # for p in pop:
        # print(p.fitness.crowding_dist)

    for idx_ind, ind in enumerate(pop):
        found_a_home = False
        mindist = 10000000
        for spec_idx, repr in enumerate(representants):
            idx_repr = [id(ind) for ind in pop].index(id(repr))
            d1 = distance_matrix[idx_repr][idx_ind]
            d2 = distance_matrix[idx_ind][idx_repr]
            # Take mean, since the distance matrix is not always symmetrical.
            dist = (d1 + d2) / 2
            mindist = min(mindist, dist)
            if dist < admission_delta:
                new_species[spec_idx].pop.append(ind)
                # print(f"Added {str(ind):<90} to new_species {spec_idx} ({len(new_species[spec_idx].pop)})")
                found_a_home = True
                break
        if not found_a_home:
            # print(f'++++++++++++ Adding species for {ind} ({mindist}) - I compared with {representants}')
            new_species.append(Species([ind]))
            representants.append(ind)
    new_species = remove_empty_species(new_species, name='split_in_species')
    # print('New species: (repr)')
    # print(representants)
    # print('New species: (sp)')
    # print(*[sp.pop for sp in new_species], sep='\n')
    npop = []
    for sp in new_species:
        npop += sp.pop
    if len(npop) != len(pop):
        print(f"{len(npop)} != {len(pop)}")
        exit(9)
    assert_unique(npop, 'end of split')

    npop = [id(p) for p in pop]
    for i in range(len(npop)):
        if npop.count(id(pop[i])) != 1:
            print(f"{id(pop[i])} ({pop[i]}) appears {npop.count(id(pop[i]))} times")
            exit(10)
    assert_nonempty_species(new_species, 'split end')
    return new_species

def get_distance_matrix(toolbox, population, dissimilarity_metric):
    # Framsticks expects list[str], not list[Individual]
    distance_matrix = toolbox.dissimilarity(population, dissimilarity_metric)
    return distance_matrix

PRINT_SP_PER_LINE = 4
def print_species_dashboard(new_species, delta):
    print_width = 58 * PRINT_SP_PER_LINE
    print(f"< {len(new_species)} species, delta {delta:.10f} >".center(print_width, '-'))
    print('-' * print_width)
    print(f"| <  uid - age > (popsize) speciesFit    representative  |" * PRINT_SP_PER_LINE)
    print('-' * print_width)
    pr_str = ''
    pr_post = []
    for i, sp in enumerate(new_species):
        repr = str(sp.get_representative()[0]).replace('\n', ' ')
        ellipsize_repr = repr if len(repr) <= 15 else f"{repr[:12]}..."
        pr_str += f"| <{sp.uid:>8}-{sp.age:>3}> ({len(sp.pop):>3} ind) {sp.species_fitness:10.5f}    {ellipsize_repr:<15} |"
        pr_post.append(repr)
        if i % PRINT_SP_PER_LINE == PRINT_SP_PER_LINE - 1:
            pr_str += f'\t\t{pr_post}\n'
            pr_post = []
    print(pr_str + (' ' * (print_width - pr_str.find('\n', -print_width) - 1)) + f"\t\t{pr_post}")
    print('-' * print_width)
    print()

def speciation(population, toolbox,
               cxpb, mutpb, ngen, dissimilarity_metric, admission_delta,
               n_species=10, interspecies_cxpb=0.001, dynamic_delta_under=0.96, dynamic_delta_over=1.33,
               restart_method='none', restart_patience=40,
               stagnant_horizon=15,
               min_species_size_for_champion_clone=5,
               stats=None, halloffame=None, verbose=__debug__):
    """
    Taken from deap, adapted for NEAT-like speciation
    """
    delta = admission_delta
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    # Split in species
    new_species = [Species(population)]
    distance_matrix = get_distance_matrix(toolbox, population, dissimilarity_metric)
    # Compute both fitness and _fitness
    new_species[0].compute_fitness(distance_matrix=distance_matrix, admission_delta=delta)
    new_pop = population
    assert_unique(new_pop, 'startall')
    popsize = len(population)

    if halloffame is not None:
        halloffame.update(new_pop)

    record = stats.compile(new_pop) if stats else {}
    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    for sp in new_species:
        record = stats.compile(sp.pop) if stats else {}
        logbook.record(gen=f"0.{sp.uid}", nevals=len(sp.pop), **record)
    if verbose:
        print(logbook.stream)
    hist = [max([p.fitness.values for p in new_pop])]
    # Begin the generational process
    for gen in range(1, ngen + 1):
        old_species = new_species
        assert_nonempty_species(old_species, 'gen begin')
        old_pop = new_pop
        new_species = [os for os in old_species] # Species are pruned later, and we need to preserve the history
        new_pop = [] # population is built up
        for sp in new_species:
            new_pop += sp.pop
        assert_unique(new_pop, 'start')

        # Compute some stats, to be able to set the mutation rate custom per species.

        # Selection:
        #  * Every species is assigned a potentially different number of offspring in proportion to the sum of
        #       adjusted fitnesses f'_i of its member organisms
        #  * Species then reproduce by first eliminating the lowest performing members from the population.
        #  * The champion of each species with more than five networks was copied into the next generation unchanged
        #  * If the maximum fitness of a species did not improve in 15 generations, the networks in the stagnant species
        #       were not allowed to reproduce
        #  * The champion of each species with more than five networks was copied into the next generation unchanged
        #  * The entire population is then replaced by the offspring of the remaining organisms in each species

        for sp in old_species:
            # Delete species if necessary
            if sp.is_stagnant(stagnant_horizon):
                new_species.remove(sp)
                print(f'Removed species {sp.uid} because it was stagnant. Max fitness:', max(sp.past_fitnesses))

        total_species_fitness = sum([max(0, sp.species_fitness) for sp in new_species])
        if total_species_fitness == 0.0:
            # Equal weights
            offspring_counts = np.array_split(np.arange(popsize), len(new_species))
            offspring_counts = [len(osc) for osc in offspring_counts]
        else:
            # FIXME: If the fitness can be negative, this doesn't work.
            offspring_counts = [((max(0, sp.species_fitness) / total_species_fitness) * popsize) for sp in new_species]
            ocdif = [int(math.floor(i)) for i in offspring_counts]
            ocd = [offspring_counts[i] - ocdif[i] for i in range(len(offspring_counts))] # float part only
            if sum(ocd) > 0:
                # Add a small delta, to allow species with 0 fitness some wiggle room.
                ocd = [(o + 1e-7) / sum(ocd) for o in ocd] # Normalized weights
                offspring_counts = random.choices(list(range(len(offspring_counts))), ocd, k=popsize - int(sum(ocdif)))
                for i in offspring_counts:
                    ocdif[i] += 1
            offspring_counts = ocdif
        #  -
        #                 (1 if len(sp.pop) >= min_species_size_for_champion_clone else 0) for sp in new_species]

        # offspring_counts = [s_int(popsize / len(new_species)) for _ in new_species]
        # offspring_counts[offspring_counts.index(max(offspring_counts))] += popsize - sum(offspring_counts)
        assert_nonempty_species(new_species, 'before sel')
        # to_delete = []
        # for i, oc in enumerate(offspring_counts):
        #     if oc == 0:
        #         to_delete.append(i)
        # # Delete the species with no offspring (idk if now or after mutation/etc)
        # for i in reversed(to_delete):
        #     new_species.pop(i)

        # if offspring_counts > popsize:
        #     for _ in range(offspring_counts - popsize):
        #         random.choice
        for idx, sp in enumerate(new_species):
            # print(f'Selecting from {len(sp.pop)}')
            # sp.pop.sort(key=lambda ind: ind.fitness.values, reverse=True)
            # print(f'--Selecting from {len(sp.pop)}')
            sp.offspring = toolbox.select(sp.pop, offspring_counts[idx])
            sp.offspring = [toolbox.clone(s) for s in sp.offspring]

        new_pop = []
        for sp in new_species:
            new_pop += sp.offspring
        assert_unique(new_pop, 'prexov')
        assert_nonempty_species(new_species, 'prexov')

        # Crossover
        #  * The interspecies mating rate was 0.001
        for sp in new_species:
            for i in range(1, len(sp.offspring), 2):
                if random.random() < cxpb:
                    if random.random() < interspecies_cxpb:
                        donor_species = random.choice(new_species)
                        donor = random.choice(donor_species.pop)
                        sp.offspring[i - 1], sp.offspring[i] = toolbox.mate(sp.offspring[i - 1], donor)
                    else:
                        sp.offspring[i - 1], sp.offspring[i] = toolbox.mate(sp.offspring[i - 1], sp.offspring[i])
                    del sp.offspring[i - 1].fitness.values, sp.offspring[i].fitness.values
        # print(f"post xov: {[len(sp.offspring) for sp in new_species]}")

        new_pop = []
        for sp in new_species:
            new_pop += sp.offspring
        assert_unique(new_pop, 'premut')
        assert_nonempty_species(new_species, 'premut')
        
        # Mutation
        #  *  In smaller populations, the probability of adding a new node was 0.03 and the probability of a new link
        #       mutation was 0.05
        #  * In the larger population, the probability of adding a new link was 0.3, because a larger population can
        #       tolerate a larger number of prospective species and greater topological diversity.
        for sp in new_species:
            # Smallest pop will get mutpb, larger ones get a multiplier on top of that
            # minnorm = min([len(sp.pop) for sp in new_species])
            # maxnorm = max([len(sp.pop) for sp in new_species])
            # sp_pbmut = mutpb * (1 + 
            #                     (((len(sp.pop) - minnorm) / (maxnorm - minnorm)) if maxnorm - minnorm > 0 else 0)
            #                     )
            sp_pbmut = mutpb # min(1.0, sp_pbmut)
            # print("Computed species pbmut:", sp_pbmut)
            for i in range(len(sp.offspring)):
                if random.random() < sp_pbmut:
                    sp.offspring[i], = toolbox.mutate(sp.offspring[i])
                    del sp.offspring[i].fitness.values
        # print(f"post mut: {[len(sp.offspring) for sp in new_species]}")

        new_pop = []
        for sp in new_species:
            new_pop += sp.offspring
        assert_unique(new_pop, 'postmut')
        assert_nonempty_species(new_species, 'postmut')

        new_pop = []
        for sp in new_species:
            # Elitism
            if sp.offspring and len(sp.offspring) > 0 and len(sp.pop) >= min_species_size_for_champion_clone:
                champion = toolbox.clone(sp.pop[0])
                sp.offspring[0] = champion
            sp.pop = sp.offspring
            del sp.offspring
            new_pop += sp.pop
        new_species = remove_empty_species(new_species, 'speciation end')
        assert_unique(new_pop, 'speciation enddd')
        assert_nonempty_species(new_species, 'after gen')
        # Eval population (maybe not needed, unless the distance is fitness)
        # print(f"pre eval: {[len(sp.pop) for sp in new_species]}")
        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in new_pop if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
        for sp in new_species:
            sp.compute_fitness(distance_matrix=distance_matrix, admission_delta=delta)

        # Split in species
        distance_matrix = get_distance_matrix(toolbox, new_pop, dissimilarity_metric)
        new_species = split_in_species(previous_species=new_species, distance_matrix=distance_matrix, admission_delta=delta)

        if len(new_species) < n_species:
            delta *= dynamic_delta_under
        elif len(new_species) > n_species:
            delta *= dynamic_delta_over

        print_species_dashboard(new_species, delta)
        
        # print('total inds:', sum([len(sp.pop) for sp in new_species]))
        if sum([len(sp.pop) for sp in new_species]) != popsize:
            exit(0)

        if halloffame is not None:
            halloffame.update(new_pop)

        assert_nonempty_species(new_species, 'logbook')
        record = stats.compile(new_pop) if stats else {}
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        for sp in new_species:
            record = stats.compile(sp.pop) if stats else {}
            logbook.record(gen=f"{gen}.{sp.uid}", nevals=len(sp.pop), **record)
        if verbose:
            print(logbook.stream)

        hist.append(max([p.fitness.values for p in new_pop]))

        # if restart_method != 'none' and len(maxFits) >= restart_patience:
        #     consider_interval = maxFits[-restart_patience:-1]
        #     bestFitPast = sorted(consider_interval, key=lambda x: x[0], reverse=True)[0]
        #     ind = consider_interval.index(bestFitPast)
        #     for mf in consider_interval:
        #         print(f"({mf[0]:10.5f})")
        #     print(len(consider_interval))
        #     print(f"{maxFits[-1][0]} <= {bestFitPast[0]} and {ind} == {restart_patience}")
        #     # bestFitPast = maxFits[-restart_patience:]
        #     if maxFits[-1][0] <= bestFitPast[0] and ind == 0:
        #         print(maxFits[-1][0], '<=', bestFitPast[0], ', doing a restart...')
        #         if restart_method == 'soft_perturb_best':
        #             print("Restarting soft_perturb_best after", restart_patience, "gens with no improvement.")
        #             population = toolbox.attr_random_pop_from_genotype(bestFitPast[1][0], len(population))
        #         elif restart_method == 'hard':
        #             print("Restarting hard after", restart_patience, "gens with no improvement.")
        #             population = toolbox.population(n=len(population))
                
        #         # Evaluate the individuals with an invalid fitness
        #         invalid_ind = [ind for ind in population if not ind.fitness.valid]
        #         fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        #         for ind, fit in zip(invalid_ind, fitnesses):
        #             print(ind)
        #             ind.fitness.values = fit

        #         if halloffame is not None:
        #             halloffame.update(population)

        #         record = stats.compile(population) if stats else {}
        #         logbook.record(gen=f"{gen}.restarting", nevals=len(invalid_ind), **record)
        #         if verbose:
        #             print(logbook.stream)
                
        #         maxFits = []

    return new_pop, logbook
