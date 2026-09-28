import onnx, numpy as np
from onnx import numpy_helper, TensorProto, helper
m = onnx.load('/home/aimfeld/Projects/Python/flawchess/frontend/public/maia/maia3_simplified.onnx')
g = m.graph
for n in g.node:
    if n.op_type == 'Cast': print('Cast', n.input, n.output, [a.i for a in n.attribute])
new_inits = []
for t in g.initializer:
    if t.data_type == TensorProto.FLOAT16:
        arr = numpy_helper.to_array(t).astype(np.float32)
        new_inits.append(numpy_helper.from_array(arr, t.name))
    else:
        new_inits.append(t)
del g.initializer[:]; g.initializer.extend(new_inits)
for n in g.node:
    for a in n.attribute:
        if n.op_type == 'Cast' and a.name == 'to' and a.i == TensorProto.FLOAT16: a.i = TensorProto.FLOAT
        if a.type == onnx.AttributeProto.TENSOR and a.t.data_type == TensorProto.FLOAT16:
            arr = numpy_helper.to_array(a.t).astype(np.float32); a.t.CopyFrom(numpy_helper.from_array(arr))
for vi in list(g.value_info) + list(g.input) + list(g.output):
    if vi.type.tensor_type.elem_type == TensorProto.FLOAT16: vi.type.tensor_type.elem_type = TensorProto.FLOAT
onnx.save(m, 'maia3_fp32.onnx')
import os; print(os.path.getsize('maia3_fp32.onnx'))
