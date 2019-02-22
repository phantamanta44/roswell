import re

import rospy

from .adapter import resolve_type

PARAM_PATTERN = r'^((?:\w+\s*:\s*\w+(?:\s*,\s*\w+\s*:\s*\w+)*|\(\)))' \
                r'(?:\s*->\s*(\w+\s*:\s*\w+(?:\s*,\s*\w+\s*:\s*\w+)*))?$'
                .replace(r'\w', '[\w_/]')


def spin(name, argstring, executor, anon=False, freq=50):
    rospy.init_node(name, anonymous=anon)

    argstring = argstring.strip()
    match = re.match(PARAM_PATTERN, argstring)
    if match is None:
        raise ValueError('Invalid argstring: ' + argstring)

    subscription_count = 0
    subscription_args_value = match.group(1)
    subscription_args = None
    if subscription_args_value.strip() != '()':
        subscription_args = subscription_args_value.split(',')
        subscription_count = len(subscription_args)
    subscription_buffer = [None] * subscription_count

    def resolve_arg(arg_str):
        split_index = arg_str.index(':')
        # calc type first because it fails catastrophically if the type doesn't exist
        arg_type = resolve_type(arg_str[split_index + 1:].strip())
        return arg_str[:split_index].strip(), arg_type

    def resolve_subscriber(arg_str, buf_index):
        def callback(value):
            subscription_buffer[buf_index] = value

        return rospy.Subscriber(*resolve_arg(arg_str), callback=callback, queue_size=1)

    def resolve_publisher(arg_str):
        return rospy.Publisher(*resolve_arg(arg_str), latch=True, queue_size=1)

    subscriptions_ready = True
    if subscription_count != 0:
        for index, arg in enumerate(subscription_args):
            resolve_subscriber(arg, index)
        subscriptions_ready = False

    publishers = None
    publication_count = 0
    publication_indices = None
    publication_arg_value = match.group(2)
    if publication_arg_value is not None:
        publishers = [resolve_publisher(arg) for arg in publication_arg_value.split(',')]
        publication_count = len(publishers)
        publication_indices = range(publication_count)

    rate_limiter = rospy.Rate(freq)
    while not rospy.is_shutdown():
        if not subscriptions_ready:
            subscriptions_ready = True
            for sub_value in subscription_buffer:
                if sub_value is None:
                    subscriptions_ready = False
                    break
        elif publication_count == 0:
            executor(*subscription_buffer)
        else:
            results = executor(*subscription_buffer)
            if publication_count == 1:
                publishers[0].publish(results)
            else:
                for i in publication_indices:
                    if results[i] is not None:
                        publishers[i].publish(results[i])
        rate_limiter.sleep()
