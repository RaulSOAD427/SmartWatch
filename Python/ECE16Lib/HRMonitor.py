from ECE16Lib.CircularList import CircularList
from sklearn.mixture import GaussianMixture as GMM  # The GMM Import
import ECE16Lib.DSP as filt
from scipy.stats import norm # Import for Gaussian PDF
import numpy as np
import matplotlib as plt
import scipy.signal as sig
import glob

"""
A class to enable a simple heart rate monitor
"""
class HRMonitor:
  """
  Encapsulated class attributes (with default values)
  """
  __hr = 0           # the current heart rate
  __time = None      # CircularList containing the time vector
  __ppg = None       # CircularList containing the raw signal
  __filtered = None  # CircularList containing filtered signal
  __num_samples = 0  # The length of data maintained
  __new_samples = 0  # How many new samples exist to process
  __fs = 0           # Sampling rate in Hz
  __thresh = 0.6     # Threshold from Tutorial 2

  """
  Initialize the class instance
  """
  def __init__(self, num_samples, fs, times=[], data=[]):
    self.__hr = 0
    self.__num_samples = num_samples
    self.__fs = fs
    self.__time = CircularList(data, num_samples)
    self.__ppg = CircularList(data, num_samples)
    self.__filtered = CircularList([], num_samples)

  """
  Add new samples to the data buffer
  Handles both integers and vectors!
  """
  def add(self, t, x):
    if isinstance(t, np.ndarray):
      t = t.tolist()
    if isinstance(x, np.ndarray):
      x = x.tolist()


    if isinstance(x, int):
      self.__new_samples += 1
    else:
      self.__new_samples += len(x)

    self.__time.add(t)
    self.__ppg.add(x)

  """
  Compute the average heart rate over the peaks
  """
  def compute_heart_rate(self, peaks):
    t = np.array(self.__time)
    return 60 / np.mean(np.diff(t[peaks]))

  """
  Process the new data to update step count
  """
  def process(self):
    # Grab only the new samples into a NumPy array
    x = np.array(self.__ppg[ -self.__new_samples: ])

    # Filter the signal (feel free to customize!)
    x = filt.detrend(x, 25)
    x = filt.moving_average(x, 5)
    x = filt.gradient(x)
    x = filt.normalize(x)

    # Store the filtered data
    self.__filtered.add(x.tolist())

    # Find the peaks in the filtered data
    _, peaks = filt.count_peaks(self.__filtered, self.__thresh, 1)

    # Update the step count and reset the new sample count
    self.__hr = self.compute_heart_rate(peaks)
    self.__new_samples = 0

    # Return the heart rate, peak locations, and filtered data
    return self.__hr, peaks, np.array(self.__filtered)

  def process_new(self):
    # Grab only the new samples into a NumPy array
    x = np.array(self.__ppg[ -self.__new_samples: ])

    # Invert PPG Signal ⇒ Detrend ⇒ Smooth ⇒ Gradient ⇒ Normalize ⇒ Find Peaks ⇒ Compute HR
    # Filter the signal (feel free to customize!)
    dt = filt.detrend(x, 25)
    # x = filt.moving_average(x, 5)
    b, a = filt.create_filter(3, 5, "lowpass", self.__fs)
    lp = filt.filter(b, a , dt)

    gradient = filt.gradient(lp)
    x = filt.normalize(gradient)

    # Store the filtered data
    self.__filtered.add(x.tolist())

    # Find the peaks in the filtered data
    _, peaks = filt.count_peaks(self.__filtered, self.__thresh, 1)

    # Update the step count and reset the new sample count
    self.__hr = self.compute_heart_rate(peaks)
    self.__new_samples = 0

    # Return the heart rate, peak locations, and filtered data
    return self.__hr, peaks, np.array(self.__filtered)


  """
  Clear the data buffers and step count
  """
  def reset(self):
    self.__hr = 0
    self.__time.clear()
    self.__ppg.clear()
    self.__filtered.clear()

  # Estimate the sampling rate from the time vector
  def estimate_fs(self, times):
    return 1 / np.mean(np.diff(times))

  # Retrieve a list of the names of the subjects
  def get_subjects(self, directory):
    filepaths = glob.glob(directory + "/*")
    return [filepath.split("/")[-1] for filepath in filepaths]

  # Retrieve a data file, verifying its FS is reasonable
  def get_data(self, directory, subject, trial, fs):
    search_key = "%s/%s/%s_%02d_*.csv" % (directory, subject, subject, trial)
    filepath = glob.glob(search_key)[0]
    t, ppg = np.loadtxt(filepath, delimiter=',', unpack=True)
    t = (t-t[0])/1e3
    hr = self.get_hr(filepath, len(ppg), fs)
    fs_est = self.estimate_fs(t)
    # if(fs_est < fs-1 or fs_est > fs):
      # print("Bad data! FS=%.2f. Consider discarding: %s" % (fs_est,filepath))

    return t, ppg, hr, fs_est

  # Estimate the heart rate from the user-reported peak count
  def get_hr(self, filepath, num_samples, fs):
    count = int(filepath.split("_")[-1].split(".")[0])
    seconds = num_samples / fs
    return count / seconds * 60 # 60s in a minute

  # Filter the signal (as in the prior lab)
  def process(self, x):
    x = filt.detrend(x, 25)
    x = filt.moving_average(x, 5)
    x = filt.gradient(x)
    return filt.normalize(x)

  # Plot each component of the GMM as a separate Gaussian
  def plot_gaussian(self, weight, mu, var):
    weight = float(weight)
    mu = float(mu)
    var = float(var)

    x = np.linspace(0, 1)
    y = weight * norm.pdf(x, mu, np.sqrt(var))
    plt.plot(x, y)

  # Estimate the heart rate given GMM output labels
  def estimate_hr(self, labels, num_samples, fs):
    peaks = np.diff(labels, prepend=0) == 1
    count = sum(peaks)
    seconds = num_samples / fs
    hr = count / seconds * 60 # 60s in a minute
    return hr, peaks

  """
  Train GMM model
  """
  
  def train(self):
    fs = 50
    directory = "./data"
    subjects = self.get_subjects(directory)

    # Leave-One-Subject-Out-Validation
    # 1) Exclude subject
    # 2) Load all other data, process, concatenate
    # 3) Train the GMM
    # 4) Compute the histogram and compare with GMM
    # 5) Test the GMM on excluded subject
    for exclude in subjects:
      print("Training - excluding subject: %s" % exclude)
      train_data = np.array([])
      for subject in subjects:
        for trial in range(1,6):
          t, ppg, hr, fs_est = self.get_data(directory, subject, trial, fs)

          if subject != exclude:
            train_data = np.append(train_data, self.process(ppg))

      # Train the GMM
      train_data = train_data.reshape(-1,1) # convert from (N,1) to (N,) vector
      gmm = GMM(n_components=2).fit(train_data)

    return gmm

  def predict(self, gmm):
      ppg_np = np.array(self.__ppg)
      test_data = self.process(ppg_np)
      labels = gmm.predict(test_data.reshape(-1,1))
      hr_est, peaks = self.estimate_hr(labels, len(self.__ppg), self.__fs)

      return hr_est