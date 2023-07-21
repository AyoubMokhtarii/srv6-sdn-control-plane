import os
import logging
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

THIS_FILE_PATH = os.path.abspath(__file__)
CONTAINING_FOLDER = os.path.dirname(THIS_FILE_PATH)
AGENT_MODELS_FOLDER = os.path.join(CONTAINING_FOLDER, '../agent_models')
AGENT_MODEL_DEFUALT_NAME = '17_07_2023__16h.30__v13_agentModel_EPIS500_BTCH128_eDEC2000_2HL128_Nt2_MaxWrngAct5.pt'


class DQN(nn.Module):

    def __init__(self, n_observations, n_actions):
        super(DQN, self).__init__()
        self.layer1 = nn.Linear(n_observations, 128)
        self.layer2 = nn.Linear(128, 128)
        self.layer3 = nn.Linear(128, n_actions)

    # Called with either one element to determine next action, or a batch
    # during optimization. Returns tensor([[left0exp,right0exp]...]).
    def forward(self, x):
        x = F.relu(self.layer1(x))
        x = F.relu(self.layer2(x))
        return self.layer3(x)



def load_trained_model(dir_name=AGENT_MODELS_FOLDER, file_name=AGENT_MODEL_DEFUALT_NAME):
    if dir_name is None or file_name is None:
        logging.error('dir_name and file_name must be specified in load_trained_model().')
        return None
    dir_path = os.path.join(dir_name)
    if not os.path.exists(dir_path):
        logging.error("The folder: ", dir_name,  " does not exist.")
        return None
    file_path = os.path.join(dir_path, file_name)
    # Check if the file exists
    if not os.path.exists(file_path):
        print("The file: ", file_name,  " does not exist.")
        return None
    
    # FIXME 2 is the number of actions == number of tunnels (FIX Number of tunnels for testing purposes).
    model = DQN(9, 2)
    model = torch.load(file_path)
    return model



# test 
if __name__ == '__main__':
    model = load_trained_model()
    print(model)