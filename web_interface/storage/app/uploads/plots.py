import matplotlib.pyplot as plt

def create_sample_plot(output_path):
    plt.figure(figsize=(6,4))
    plt.plot([1,2,3,4], [10,20,25,30], marker='o')
    plt.title('Sample Plot')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
