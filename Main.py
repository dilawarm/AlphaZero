# Importing files from this project
import ResNet
import MCTS
import Multiprocessing

import time

# from TicTacToe import Gamelogic
# from TicTacToe import Config
from FourInARow import Gamelogic
from FourInARow import Config

# from keras.optimizers import SGD
# from loss import softmax_cross_entropy_with_logits, softmax

import numpy as np


# Creating and returning a tree with properties specified from the input
def get_tree(config, agent, game, dirichlet_noise=True, seed=0):
    tree = MCTS.MCTS()  # (game, game.get_board(), None, config)
    tree.dirichlet_noise = dirichlet_noise
    tree.NN_input_dim = config.board_dims
    tree.policy_output_dim = config.policy_output_dim
    tree.NN_output_to_moves_func = config.NN_output_to_moves
    tree.move_to_number_func = config.move_to_number
    tree.number_to_move_func = config.number_to_move
    tree.set_evaluation(agent)
    tree.set_game(game)
    print("setting seed", seed)
    tree.set_seed(seed)
    return tree


def get_game_object():
    return Gamelogic.FourInARow()


class GameGenerator:
    def __init__(self, config, agent, seed=0):
        self.game = get_game_object()
        self.tree = get_tree(config, agent, self.game, seed=seed)
        self.history = []
        self.policy_targets = []
        self.player_moved_list = []
        self.positions = []

    def run_part1(self):
        return self.tree.search()

    def run_part2(self, result):
        self.tree.backpropagate(result)
        return self

    def execute_best_move(self):
        state = self.game.get_state()
        temp_move = self.tree.get_temperature_move(state)
        print(self.tree.get_prior_probabilities(state))
        print("temp move", temp_move, self.tree.seed)
        self.history.append(temp_move)
        self.policy_targets.append(np.array(self.tree.get_posterior_probabilities(state)))
        self.player_moved_list.append(self.game.get_turn())
        self.positions.append(np.array(self.game.get_board()))
        self.game.execute_move(temp_move)
        return self, self.game.is_final()

    def reset_tree(self):
        self.tree.reset_search()
        # self.tree.root.board_state = self.game.get_board()

    def get_results(self):
        game_outcome = self.game.get_outcome()
        value_targets = [game_outcome[x] for x in self.player_moved_list]
        return self.history, self.positions, self.policy_targets, value_targets


# Generating data by self-play
def generate_data(result_queue, game, res_dict, config1, num_sim, seed, games=1, num_search=130):
    import tensorflow as tf
    import ResNet as ResNet_p
    from keras.backend.tensorflow_backend import set_session
    print("Starting", result_queue)
    # config = tf.ConfigProto()
    # config.gpu_options.allow_growth = True  # dynamically grow the memory used on the GPU
    # config.log_device_placement = True  # to log device placement (on which device the operation ran)
    # # (nothing gets printed in Jupyter, only if you run it standalone)
    # sess = tf.Session(config=config)
    # set_session(sess)  # set this TensorFlow session as the default session for Keras
    # Assume that you have 12GB of GPU memory and want to allocate ~4GB:
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.08)

    sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))
    set_session(sess)
    # game=inp[1]
    # res_dict=inp[2]
    # config=inp[3]
    from keras.optimizers import SGD
    from loss import softmax_cross_entropy_with_logits, softmax
    agent = ResNet_p.ResNet.build(6, 7, 2, 128, config1.policy_output_dim, num_res_blocks=7)

    game_generators = [GameGenerator(config1, agent, seed=seed) for _ in range(num_sim)]

    x = []
    y_policy = []
    y_value = []

    while len(game_generators):
        # print("test1")
        res = [game_generator.reset_tree() for game_generator in game_generators]
        for i in range(num_search):
            # print("test2")
            res = [game_generator.run_part1() for game_generator in game_generators]
            # print("test3")
            to_predict = []
            to_predict_generators = []
            no_predict_generators = []
            for i in range(len(res)):
                # print("test4")
                if res[i] is not None:
                    to_predict.append(res[i])
                    to_predict_generators.append(game_generators[i])
                else:
                    no_predict_generators.append(game_generators[i])
                # print("test5")
            # print("test6")
            if len(to_predict):
                # print("to_predict", to_predict)
                batch = np.array(to_predict)
                results = agent.predict(batch)
                # TODO: must use softmax
                # print("result", results)
            # print("test7")
            [to_predict_generators[i].run_part2(np.array([results[0][i], results[1][i][0]])) for i in
             range(len(to_predict_generators))]
            # print("test8")
            [no_predict_generators[i].run_part2(None) for i in range(len(no_predict_generators))]
            # print("test9")

        print("LEN", len(game_generators))

        res = [game_generator.execute_best_move() for game_generator in game_generators]
        game_generators = []
        finished_games = []
        for game_generator, finished in res:
            if finished:
                finished_games.append(game_generator)
                continue
            game_generators.append(game_generator)
        game_results = [game_generator.get_results() for game_generator in finished_games]
        for moves, history, policy_targets, value_targets in game_results:
            print("moves", moves)
            x.extend(history)
            y_policy.extend(policy_targets)
            y_value.extend(value_targets)

    print("finished", )
    res_dict[str(result_queue)] = [x, y_policy, y_value]


# # Generating data by self-play
# def generate_data(game, agent, config, num_sim=100, games=1):
#     tree = get_tree(config, agent, game)
#
#     x = []
#     y_policy = []
#     y_value = []
#
#     for curr_game in range(games):
#
#         game.__init__()
#         history = []
#         policy_targets = []
#         player_moved_list = []
#         positions = []
#
#         while not game.is_final():
#             tree.reset_search()
#             print("num_sim", num_sim)
#             tree.search_series(num_sim)
#             state = game.get_state()
#             temp_move = tree.get_temperature_move(state)
#             print("move:", temp_move)
#             print("temp_probs:", tree.get_temperature_probabilities(state))
#             history.append(temp_move)
#             policy_targets.append(np.array(tree.get_posterior_probabilities(state)))
#             print("prior_probs:", tree.get_prior_probabilities(state)) #reshape(1,3,3,2)
#             print("pol_targets", policy_targets[-1])
#             player_moved_list.append(game.get_turn())
#             positions.append(np.array(game.get_board()))
#
#             game.execute_move(temp_move)
#
#         game_outcome = game.get_outcome()
#         value_targets = [game_outcome[x] for x in player_moved_list]
#         print("val_targets:", value_targets)
#
#         x = x + positions
#         y_policy = y_policy + policy_targets
#         y_value = y_value + value_targets
#
#         print("History:", history)
#
#     return np.array(x), np.array(y_policy), np.array(y_value)


# Training AlphaZero by generating data from self-play and fitting the network
def train(game, config, num_filters, num_res_blocks, num_sim=10, epochs=1000000, games_each_epoch=10,
          batch_size=32, num_train_epochs=10):
    h, w, d = config.board_dims[1:]
    # agent.summary()

    for epoch in range(epochs):
        # for processes in [2]:
        #     for games_pr_process in [2]:
        #         now = time.time()
        #         x, Y_pol, y_val=Multiprocessing.multiprocess_function(processes, game, None, Config, games=games_pr_process)
        #         # x, y_pol, y_val = Multiprocessing.multiprocess_function(4, game, None, Config)
        #         # x, y_pol, y_val = generate_data(None, game, agent, config, num_sim=num_sim, games=games_each_epoch)
        #         print(processes, games_pr_process, "Time_taken", time.time() - now, "pr game",
        #               (time.time() - now) / (processes * games_pr_process))
        x, y_pol, y_val=Multiprocessing.multiprocess_function(2, game, None, Config, games=2)
        from keras.optimizers import SGD
        from loss import softmax_cross_entropy_with_logits, softmax
        # agent = ResNet.ResNet.build(h, w, d, num_filters, config.policy_output_dim, num_res_blocks=num_res_blocks)
        # agent.compile(loss=[softmax_cross_entropy_with_logits, 'mean_squared_error'],
        #               optimizer=SGD(lr=0.0005, momentum=0.9))
        # print("Epoch")
        # # print("x", x, x.shape)
        # # print("y_pol", y_pol, y_val.shape)
        # # print("y_val", y_val, y_val.shape)
        # agent.fit(x=x, y=[y_pol, y_val], batch_size=min(batch_size, len(x)), epochs=num_train_epochs, callbacks=[])
        # print("end epoch")
        # if (epoch % 10 == 0):
        #     agent.save_weights("Models/" + Config.name + "/" + str(epoch) + "_batch.h5")
        print("_____________--------------_____________")
        time.sleep(10)
    return agent


def choose_best_legal_move(legal_moves, y_pred):
    best_move = np.argmax(y_pred)
    print("Best move", best_move)
    if (y_pred[best_move] == 0):
        return None
    if best_move in legal_moves:
        return best_move
    else:
        y_pred[best_move] = 0
        return choose_best_legal_move(legal_moves, y_pred)


if __name__ == '__main__':
    train(Gamelogic.FourInARow(), Config, 128, 0)
