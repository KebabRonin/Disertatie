import random
from deap import tools
import math

def annealer(population, toolbox, lbda, ngen, autolambda=True,
                   stats=None, halloffame=None, verbose=__debug__):
    logbook = tools.Logbook()
    logbook.header = ['gen', 'nevals'] + (stats.fields if stats else [])

    assert len(population) == 1

    # Evaluate the individuals with an invalid fitness
    invalid_ind = [ind for ind in population if not ind.fitness.valid]
    fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
    for ind, fit in zip(invalid_ind, fitnesses):
        ind.fitness.values = fit

    if halloffame is not None:
        halloffame.update(population)

    record = stats.compile(population) if stats is not None else {}
    logbook.record(gen=0, nevals=len(invalid_ind), **record)
    if verbose:
        print(logbook.stream)

    # Begin the generational process
    for gen in range(1, ngen + 1):
        print('pop', population)
        print(list(map(id, population)))
        # The population only has one individual, so just mutate it lambda times.
        # toolbox.mutate()[0] because it returns a tuple with one element, so we need to unwrap the deap.Individual
        offspring = []
        for _ in range(int(math.floor(lbda))):
            offspring1, = toolbox.mutate(toolbox.clone(population[0]))
            del offspring1.fitness.values
            offspring.append(offspring1)
        assert len(offspring) == math.floor(lbda), f"{len(offspring)} != {math.floor(lbda)}"
        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
        print('osmut', offspring)
        print(list(map(id, offspring)))

        record = stats.compile(offspring) if stats is not None else {}
        logbook.record(gen=f"{gen}.mutate", nevals=len(invalid_ind), **record)

        offspring.sort(key=lambda ind: ind.fitness.values, reverse=True)
        best_mutated_offspring = offspring[0]

        # Update the hall of fame with the generated individuals
        if halloffame is not None:
            halloffame.update(offspring)

        # The population only has one individual, so just mutate it lambda times.
        offspring = []
        for _ in range(math.floor(lbda)):
            if len(offspring) == math.floor(lbda):
                break
            assert len(offspring) < math.floor(lbda)

            offspring1, offspring2 = toolbox.mate(toolbox.clone(population[0]), toolbox.clone(best_mutated_offspring))
            del offspring1.fitness.values, offspring2.fitness.values

            if math.floor(lbda) - len(offspring) == 1:
                offspring.append(random.choice([offspring1, offspring2]))
            else:
                offspring.append(offspring1)
                offspring.append(offspring2)

        # Evaluate the individuals with an invalid fitness
        invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
        fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        print('osmate', offspring)
        print(list(map(id, offspring)))
        record = stats.compile(offspring) if stats is not None else {}
        logbook.record(gen=f"{gen}.mate", nevals=len(invalid_ind), **record)

        offspring.append(best_mutated_offspring) # !!!
        offspring.sort(key=lambda ind: ind.fitness.values, reverse=True)
        best_mated_offspring = offspring[0]

        # Update the hall of fame with the generated individuals
        if halloffame is not None:
            halloffame.update(offspring)

        if autolambda:
            prev_lbda = lbda
            if best_mated_offspring.fitness.values > population[0].fitness.values:
                lbda = lbda / F
            else:
                lbda = lbda * (F ** (1/4))
            print(f"[Autolambda] Updated lambda value to be {lbda} (was {prev_lbda})")
            lbda = max(1, lbda)
        print(f'Comparing {best_mated_offspring.fitness.values} with {population[0].fitness.values}')
        # Allow fitness-neutral improvements, otherwise you'll never leave the starting genotype.
        if best_mated_offspring.fitness.values >= population[0].fitness.values:
            print(f'Fitness {best_mated_offspring.fitness.values} was better than {population[0].fitness.values}, replacing...')
            population[0] = best_mated_offspring

        # Update the statistics with the new population
        record = stats.compile(population) if stats is not None else {}
        logbook.record(gen=gen, nevals=len(invalid_ind), **record)
        if verbose:
            print(logbook.stream)

