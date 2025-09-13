import pickle

def pickle_read(filename: str):
    with open(filename + ".pkl", "rb") as f:
        loaded_data = pickle.load(f)
    return loaded_data
def pickle_write(data, filename: str):
    with open(filename + ".pkl", "wb") as f:
        pickle.dump(data, f)