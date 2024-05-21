def gradient_descent(target, initial_stress, learning_rate=0.1, tolerance=1e-5, max_iterations=100):
    current_stress = initial_stress
    for _ in range(max_iterations):
        current_displacement = background_calc(current_stress)
        error = current_displacement - target
        if abs(error) < tolerance:
            break
        current_stress -= learning_rate * error
    return current_stress


def gradient_descent_v2(target, initial_stress, learning_rate=0.1, tolerance=1e-5, max_iterations=100):
    current_stress = initial_stress
    for _ in range(max_iterations):
        current_displacement = background_calc(current_stress)
        error = current_displacement - target
        if abs(error) < tolerance:
            break
        current_stress -= learning_rate * error * 0.9  # Slightly different learning rate adjustment
    return current_stress


def adam_optimizer(target, initial_stress, learning_rate=0.1, tolerance=1e-5, max_iterations=100, beta1=0.9, beta2=0.999, epsilon=1e-8):
    current_stress = initial_stress
    m, v = 0, 0
    for t in range(1, max_iterations + 1):
        current_displacement = background_calc(current_stress)
        error = current_displacement - target
        if abs(error) < tolerance:
            break
        g = error
        m = beta1 * m + (1 - beta1) * g
        v = beta2 * v + (1 - beta2) * (g ** 2)
        m_hat = m / (1 - beta1 ** t)
        v_hat = v / (1 - beta2 ** t)
        current_stress -= learning_rate * m_hat / (np.sqrt(v_hat) + epsilon)
    return current_stress


def nelder_mead(target, initial_stress, tolerance=1e-5, max_iterations=100):
    def objective(stress):
        return abs(background_calc(stress) - target)

    result = minimize(objective, initial_stress, method='Nelder-Mead', options={'xatol': tolerance, 'maxiter': max_iterations})
    return result.x[0]


def simple_iteration(target, initial_stress, learning_rate=0.1, tolerance=1e-5, max_iterations=100):
    current_stress = initial_stress
    for _ in range(max_iterations):
        current_displacement = background_calc(current_stress)
        error = current_displacement - target
        if abs(error) < tolerance:
            break
        current_stress -= learning_rate * np.sign(error)
    return current_stress


if __name__ == '__main__':
    optimal_stress_gd1 = gradient_descent(TARGET_DIAPLACEMENT, INITIAL_STRESS)
    optimal_stress_gd2 = gradient_descent_v2(TARGET_DIAPLACEMENT, INITIAL_STRESS)
    optimal_stress_adam = adam_optimizer(TARGET_DIAPLACEMENT, INITIAL_STRESS)
    optimal_stress_nm = nelder_mead(TARGET_DIAPLACEMENT, INITIAL_STRESS)
    optimal_stress_si = simple_iteration(TARGET_DIAPLACEMENT, INITIAL_STRESS)

    print(f'Optimal stress (Gradient Descent 1): {optimal_stress_gd1}')
    print(f'Optimal stress (Gradient Descent 2): {optimal_stress_gd2}')
    print(f'Optimal stress (Adam): {optimal_stress_adam}')
    print(f'Optimal stress (Nelder-Mead): {optimal_stress_nm}')
    print(f'Optimal stress (Simple Iteration): {optimal_stress_si}')
