import sys
sys.path.append('.')
import importlib
m = importlib.import_module('VAT_Invoice_Processor')
print('Imported OK')
print('ENABLE_PARALLEL_IMPORT:', getattr(m, 'ENABLE_PARALLEL_IMPORT', None))
print('WORKER_COUNT:', getattr(m, 'WORKER_COUNT', None))
