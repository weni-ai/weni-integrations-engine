import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
proc_name = "marketplace"
default_proc_name = proc_name
accesslog = "-"
errorlog = "-"
capture_output = True
timeout = 120
bind = "0.0.0.0"
