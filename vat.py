import tensorflow as tf
import numpy
import sys, os

import layers as L
import cnn

FLAGS = tf.app.flags.FLAGS

tf.app.flags.DEFINE_float('epsilon', 1e-6, "norm length for (virtual) adversarial training ")
tf.app.flags.DEFINE_integer('num_power_iterations', 1, "the number of power iterations")
tf.app.flags.DEFINE_float('xi', 1e-6, "small constant for finite difference")


def logit(x, is_training=True, update_batch_stats=True, stochastic=True, seed=1234):
    return cnn.logit(x, is_training=is_training,
                     update_batch_stats=update_batch_stats,
                     stochastic=stochastic,
                     seed=seed)


def forward(x, is_training=True, update_batch_stats=True, seed=1234):
    if is_training:
        return logit(x, is_training=True,
                     update_batch_stats=update_batch_stats,
                     stochastic=True, seed=seed)
    else:
        return logit(x, is_training=False,
                     update_batch_stats=update_batch_stats,
                     stochastic=False, seed=seed)


def get_normalized_vector(d):
    d /= (1e-12 + tf.reduce_max(tf.abs(d), range(1, len(d.get_shape())), keep_dims=True))
    d /= tf.sqrt(1e-6 + tf.reduce_sum(tf.pow(d, 2.0), range(1, len(d.get_shape())), keep_dims=True))
    return d


# u is normalized adversarial perturbation
# returns an improved normalized adversarial perturbation
def generate_virtual_adversarial_perturbation(x, u, logit, is_training=True):
    d = u

    for _ in range(FLAGS.num_power_iterations):
        d = FLAGS.xi * d
        logit_p = logit
        logit_m = forward(x + d, update_batch_stats=False, is_training=is_training)
        # TODO use L2 instead. not just here but in virtual_adversarial_loss
        dist = L.kl_divergence_with_logit(logit_p, logit_m)
        grad = tf.gradients(dist, [d], aggregation_method=2)[0]
        d = tf.stop_gradient(grad)
        d = get_normalized_vector(d)

    return d


def virtual_adversarial_loss(x, u, logit, is_training=True, name="vat_loss"):
    u_prime = generate_virtual_adversarial_perturbation(x, u, logit, is_training=is_training)
    logit = tf.stop_gradient(logit)
    logit_p = logit
    logit_m = forward(x + FLAGS.epsilon * u_prime, update_batch_stats=False, is_training=is_training)
    loss = L.kl_divergence_with_logit(logit_p, logit_m) / FLAGS.epsilon
    return tf.identity(loss, name=name), u_prime


def generate_adversarial_perturbation(x, loss):
    raise "don't go here"
    grad = tf.gradients(loss, [x], aggregation_method=2)[0]
    grad = tf.stop_gradient(grad)
    return FLAGS.epsilon * get_normalized_vector(grad)


def adversarial_loss(x, y, loss, is_training=True, name="at_loss"):
    raise "don't go here"
    r_adv = generate_adversarial_perturbation(x, loss)
    logit = forward(x + r_adv, is_training=is_training, update_batch_stats=False)
    loss = L.ce_loss(logit, y)
    return loss
