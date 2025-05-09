"""Consts Data"""
REFER_IMG_COLOR = (238, 0, 0)


"""Parameters for Layer Analysis"""
# threshold for distinct small groups and trustful large group(might be folded)
# Value of this threshold supposed to be low
# crossed echo groups with size that below this threshold will process surrounding analysis
# Note that this threshold is not suggested to be too large because small group that surrounded by total opposite velocity mode
# echoes is regarded as isolated and will be removed if it's size is smaller that this threshold
SMALL_GROUP_SIZE_THRESHOLD = 35

# threshold of layer gap between valid below echoes or valid surrounding echoes
# and the layer echoes that need to add upon
# value supposed to be between 2 and 3
LAYER_GAP_THRESHOLD = 2.25

# threshold for determine whether an echo groups
# has valid surroundings or not for adding or filling
# threshold value supposed to be less than 0.5 be better not too low
VALID_SURROUNDED_ECHO_RATIO_THRESHOLD = 0.28

# threshold for determine whether a basemaps echo groups is allowed
# to be filled basemaps on the valid surroundings or not
# threshold value supposed to be high
BASE_ECHO_SURROUNDED_RATIO_THRESHOLD = 0.75


"""Parameters for Velocity Integration"""
# threshold for determine whether a crossed echo group is included by one specific mode of velocity echo
# which is used for check inclusion relationship of ned including pos echoes or reversing
CROSSED_ECHOES_INCLUSION_CHECK_THRESHOLD = 0.79

# threshold for decide whether echo get folded or not
FOLDED_ECHO_CHECK_THRESHOLD = 6.5

# threshold for opposite mode echo group integration check
CROSSED_SMALL_GROUP_SURROUNDING_GAP_THRESHOLD = 4.45


"""Parameters for Velocity Unfold"""
# threshold for velocity unfold neighbour surrounded ratio check
OPPOSITE_SURROUNDED_THRESHOLD = 0.1

# threshold for indicating how much do opposite echoes compose in the valid surrounding echoes of the group
OPPOSITE_COMPOSE_THRESHOLD = 0.98

# number of layer that might contain folded echo
FOLDED_LAYER_NUM = 3
