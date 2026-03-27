# **GECCO 2026: Automated Design Competition**
## Working Area



**NotebookLM** for generating diagrams for the pptx

Baseline (adaptMut with default FramsticksEvolution): 286 MB (14.01% of RAM budget)
With simple data collection for each evaluation: 462 MB (22.56% of RAM budget) \[+8.55%\]


### Source Index
*Sorted by relevancy. Notes about each source in the footnotes.*

**Drones**
- Human-Computer Interaction/Practical Experiments[^robots-firefighter-perception] [^robots-rescuer-opinion] [^robots-evolve-behavior]
- Algorithms [^robots-gradient-perception] [^robots-evolve-behavior] [^robots-abstract-map] [^robots-aco-routing] [^robots-enn] 
- Reviews/Surveys [^robots-swarm-review] [^robots-SLAM-review] [^robots-uav-sar-survey]

**Games** [^npc-bachelor-sisyphus-neat] [^npc-behavior-tree-optimisation] [^npc-bachelor-variety-ga]

**Offtopic** [^robots-morphology] [^npc-behavior-emotions]

**General Algorithms** [^map-elites] [^rl-evo-comparison] [^quality-diversity]
### Alternate Topics
* Drone Swarm Strategies for Search and Rescue missions
* Genetic evolution of monsters in video games
	- Random Bachelor thesis[^NPC-bachelor-sisyphus-neat], looks like what I had in mind for this topic
	- Maybe make a more complex game/controller as a thesis?
* Thesis to run experiments for NPC behavior tree optimisation? [^npc-behavior-tree-optimisation]
## Implementation:
- Use [OpenAI gym](https://github.com/XHR-ZJU/rl-pybullet-drones) as physics simulator (alternative?: [Drone Watch And Rescue](https://github.com/vrodriguezf/dwr))
- Use co-evolution for test environments/victim placement? Maybe VAE?
	- If procedurally generating test scenarions, could maybe identify some parts which are easy/hard for drones to navigate (like having a certain room shape which confuses drones, which can be used as a building block in test scenarions)
- To look into real life limitations/costs/available sensors for drones 
- Papers frequently use simulations with questionable applicability to real life[^robots-swarm-review], this[^robots-gradient-perception] used kinematic simulation + physics simulation + real life tests
- Drones should create some kind of map to lead rescuers to victims, could maybe lead conscious victims to safety?
	- A research direction could include a system to assign roles for human rescuers 
- Use messenger drones to communicate instructions from base of operations?
- Establish ad hoc bases of operations/repeaters?
	- In the disaster zone, hand picked locations probably
	- Could be used as waypoints, stable databases, etc.
### Features:
- Maps for human rescuers:
	- Abstract maps[^robots-abstract-map] (goto Big Tree 20° left-> goto Yellow Building enter -> goto 3rd door on the right -> VICTIM)
	- SLAM - actual maps
	- Map merging algorithms/How to transmit the map to operations base?
- Hazards (for humans and/or for robots):
	- no-signal zones
	- no-go for humans/robots, limited-time spent in some zones
	- dynamic updates (collapsing floors, fire spread, etc.)
- Victim behavior:
	- Unconscious/conscious, degrees of injury, Wandering behaviors, Cries of help
	- Follow drones to rescue zone?
- Simulate human rescuers
- Meta:
	- Simulation recordings
	- Map debug view to follow a drone over a simulation
	- Cost calculator (nr. drones, types, total energy consumed (cost of recharge), IoT: CPU/GPU cycles used, memory used)
### Stretch goals:
- Modular sensor configuration (could be used to set up real life available resources for rescue teams)
- Measure data efficiency: generations/frames <-> fitness (should have alternative algorithms to compare)
- Create maps of checked locations (who checked where, record paths of the humans)
- Evolve robot morphologies[^robots-morphology]
	- Would need a good simulator & a good selection of base components to combine & a good generator
## Algorithms
- GA, NEAT/EANT
- Take into account sensor readings + speed/direction of neighbors for emergent communication[^robots-gradient-perception]
- ACO for data routing[^robots-aco-routing]
- Use behavior trees evolution?[^npc-behavior-tree-optimisation] Simple NN[^robots-evolve-behavior]?
- Quality-Diversity for exploration?[^quality-diversity] Novelty search (need distance function)? MAP-Elites? [^map-elites] Bayesian optimisation (optuna)?
- Evolutionary Reinforcement Learning? [^robots-enn]
- For SLAM and map merging: Occupancy Grids? (determine density of sensor data points around obstacles)
## Keywords:

**SLAM**: Simultaneous Localization And Mapping

**UAV**: Unmanned Air Vehicle

**Swarm SLAM**: Many expendable robots

**Multi-robot SLAM**: Many costly robots

## Sources

[^robots-gradient-perception]: [Collective gradient perception with a flying robot swarm](https://link.springer.com/content/pdf/10.1007/s11721-022-00220-1.pdf) - Swarm Intelligence Journal (Oct 2022)
	- Ordered and cohesive collective motion, while not exchanging information between the agents directly
	- Boids with differing speed/distance to neighbors depending on local measurements
	- Inspired by bees waiting X seconds depending on the local temperature or fish going X m/s depending on local light levels
	- Speed Modulation and Desired Distance Modulation: modify speed and distance to neighbors proportionally to the local measurement
	- No need to program alignment control, you can use on-board sensors to keep your distance from others
	- Kinematic simulator + Physics-based simulator ([OpenAI gym](https://github.com/XHR-ZJU/rl-pybullet-drones)) + Real life nano-drone experiments
	- Velocity commands -> instructions can be used for ground and air drones
	- Possible extension to dynamic gradient, predator-prey situation
	- Can be used to detect gas leaks

[^robots-evolve-behavior]: [Evolution of Adaptive Behaviour in Robots by Means of Darwinian Selection](https://journals.plos.org/plosbiology/article/file?id=10.1371/journal.pbio.1000292&type=printable) - PLoS Biology (Jan 2010)
	- Evolve neural net weights, small Neural Nets (~sensors x actions neurons)
	- Experiments with real life robots. predator-prey, evolving physical body configuration, foraging

[^robots-abstract-map]: [Robot Navigation in Unseen Spaces using an Abstract Map](https://arxiv.org/pdf/2001.11684) - IEEE Transactions on Cognitive and Developmental System (May 2020)
	- Use landmarks, angles & distances to orient, not metric maps

[^robots-aco-routing]: [AntHocNet: An Adaptive Nature-Inspired Algorithm for Routing in Mobile Ad Hoc Networks](https://cs.unibo.it/bison/publications/IDSIA-27-04.pdf) - European transactions on telecommunications (2005)

[^rl-evo-comparison]: [Evolution Strategies as a Scalable Alternative to Reinforcement Learning](https://arxiv.org/pdf/1703.03864) - (Sep 2017)
	- Centers on comparison between Reinforcement Learning and Evolutionary Strategies, comparing runtime and data used

[^robots-swarm-review]: [A Systematic Review of Swarm Robots](https://www.researchgate.net/publication/342298390_A_Systematic_Review_of_Swarm_Robots) - Current Journal of Applied Science and Technology (Jun 2020)
	- Swarm robots can be used for medical interventions (miniaturization, blood clots)
	- Swarm/drone experiments research mostly through simulators
	- Task distribution: centralized (bidding system) or threshold (more decentralized)

[^robots-SLAM-review]: [Swarm SLAM: Challenges and Perspectives](https://pmc.ncbi.nlm.nih.gov/articles/PMC8010569/) - Frontiers in Robotics and AI (Mar 2021)
	- Swarm SLAM is a recent field (2019 onwards)
	- Cost is a real concern
	- Path planning is often used, limited exploration
	- Map-merging
	- Swarm SLAM (many inexpensive and disposable robots) vs Multi-robot SLAM (you'd hate to lose a robot)
	- Sensors are not perfect

[^robots-enn]: [Towards Behavior Control for Evolutionary Robot Based on RL with ENN](https://journals.sagepub.com/doi/epub/10.5772/53992)
	- Behavior-switching control strategy based on NN and GA
	- NN sub-networks for different behaviors, evolved through GA
	- Subnetworks are piped through each other (nr inputs = nr outputs) to get the output
	- I don't understand it, NEAT-like?

[^robots-rescuer-opinion]: [Case Study No.11: Simulation – Drones for Search and Rescue in Emergency Response](https://capacity4dev.europa.eu/discussions/case-study-no11-simulation-drones-search-and-rescue-emergency-response_en) -  EU Site (May 2023)
	- Non-autonomous drones, they required a human operator
	- Drone imaging preferred over satellite map, but it takes a long time to create (2h)
	- Thermal camera less useful in hot environments
	- eBee, albris (formerly called eXom) and one MD4-200 microdrone were used
	- Most useful for live-video assessments of severity/required resources 
	- Live-feed is very costly, base of operations was 2km from the event site
	- Drones cannot match the precision and ability of animals (dogs were still used)
	- Scent, sound to consider

[^robots-firefighter-perception]: [Firefighters' Perceptions on Collaboration and Interaction with Autonomous Drones: Results of a Field Trial](https://arxiv.org/abs/2405.10153) - In Proceedings CHI Conference (May 2024)
	- Non-autonomous drones, they required a human operator
	- Drones with infrared sensors for fire source detection, or for communication and time-saving, Water needs to consider
	- Human-Drone communication & trust are essential
	- "a virtual model capable of providing an overall situation and assigning roles to participants"
	- "two-role drone system providing support for scouting, evacuation, and rescue": scout & solider/seeker
	- Motor, reactive, and cognitive drone autonomy
	- Human-Drone Interaction through light >> voice >>> (less useful) gesture/touch/brain-computer
	- Distinction between commander (central decisionmaking point) and 'regular' firefighters (+ drone officer for experiment)
	- Improvements requested: detect potential (flammable) hazards, smart helmets with HUD, reduce information overload (filter info by urgency, role)
	- Drone models used: DJI Matrice 30 (location reporting via Flighthub 2), DJI Avata
	- Important that humans have the final say

[^robots-morphology]: [Unconventional Hexacopters via Evolution and Learning: Performance Gains and New Insights](https://arxiv.org/html/2505.14129v1) - (May 2025)
	- GA represents morphologies > each morphology gets a controller through Reinforcement Learning > Compute fitness
	- PPO (actor-critic) for RL
	- Evolved morphologies were better on the tasks they were trained on than human designs

[^npc-bachelor-sisyphus-neat]: [Evolving Enemy Behavior in Video Games](https://egrove.olemiss.edu/cgi/viewcontent.cgi?article=4501&context=hon_thesis) - (2025)
	- NEAT
[^npc-behavior-tree-optimisation]: [Boosting Cooperative NPC Effectiveness and Player Immersion through Behavior Tree Optimization in Gaming](https://www.ewadirect.com/proceedings/ace/article/view/20547)
	- Combining Monte Carlo Tree Search (like minmax with simulated n steps ahead) with NN could create intelligent and adaptive game opponents
	- No experiment done in the paper, only speculation. Maybe run this as a master thesis?

[^npc-bachelor-variety-ga]: [Adding Variety in NPCs Behaviour Using Emotions and Genetic Algorithms: the GENIE Project](https://air.unimi.it/retrieve/dfa8b9a6-fb2d-748b-e053-3a05fe0a3a96/CoG-19_paper_71.pdf)
	- Use genetic algorithms to spawn enemies which are challenging, but not too much
	- Don't clone those who kill player, clone those which last long
	- Shoddy procedure, no control group, subjective metric
	- Emotions = states (Forgetful, Paranoid, Bold, Strategic)
	- Applied to multiple game prototypes in multiple genres

[^npc-dota-pso]: [Utilization of the Particle Swarm Optimization Algorithm in Game Dota 2] - (2024)
	- PSO/GA run per frame to decide jungle/push/defend/farm
	- Strong against low-mid MMR

[^npc-behavior-emotions]: [Development of Non-Player Character with Believable Behavior: a systematic literature review](https://www.sbgames.org/proceedings2021/ComputacaoShort/217749.pdf)
	- Engagement based on player perception (role, personality, emotions), challenge and predictablity

[^npc-unreal-ga-finetuning]: [USING GENETIC ALGORITHMS TO EVOLVE CHARACTER BEHAVIOURS IN MODERN VIDEO GAMES](https://csd.uwo.ca/~mkatchab/pubs/gameonna2008_unreal.pdf)
	- Evolve unreal tournament bots, just finetuning with AG, params like jumpiness(bhopping), attentiveness, etc already programmed in (?)
	- Selection: drop those bots who killed the player and those who last the least time
	- Didn't test for player enjoyability

[^npc-golem]: [GOLEM: Generator Of Life Embedded into MMOs](https://direct.mit.edu/isal/proceedings/ecal2013/25/585/98928) - (Sep 2013)
	- Basic AG applied to D&D beasts

[^npc-bachelor-ga-game]: [Monsters of Darwin: a strategic game based on Artificial Intelligence and Genetic Algorithms](https://ceur-ws.org/Vol-1956/GHItaly17_paper_05.pdf) - (Apr 2017)
	- Random bachelor thesis

[^quality-diversity]: [Evaluating Human–Robot Interaction Algorithms in Shared Autonomy via Quality Diversity Scenario Generation](https://dl.acm.org/doi/pdf/10.1145/3476412)

[^map-elites]: [Illuminating search spaces by mapping elites](https://arxiv.org/abs/1504.04909) - Early Draft (Apr 2015)
	- Map out well performing solutions (defined in a high dimensional space) over some features of interest (cost, resource type used, etc.)
	- GA which remembers the best for each cell in a grid (grid of 2-3d, to be visualizable)

[^robots-uav-sar-survey]: [Unmanned Aerial Vehicles for Search and Rescue: A Survey](https://www.researchgate.net/publication/371899272_Unmanned_Aerial_Vehicles_for_Search_and_Rescue_A_Survey)
