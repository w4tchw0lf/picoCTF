import numpy as np

def rotation_axis_from_matrix(matrix):
    """
    En este modelo, los engranajes giran alrededor de su eje local Y.
    La segunda columna de la matriz 3x3 indica ese eje en coordenadas globales.
    """
    m = np.asarray(matrix, dtype=float).reshape(4, 4)

    axis = m[:3, 1]
    norm = np.linalg.norm(axis)

    if norm == 0:
        raise ValueError("Matriz con eje de giro inválido")

    axis /= norm

    # Redondear porque las matrices contienen pequeños errores decimales.
    axis[np.abs(axis) < 1e-6] = 0
    return tuple(np.round(axis, 4))
