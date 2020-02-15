class ParticipationNotAllowed(Exception):
    """The voter is not assigned or not allowed to vote for question"""
    pass


class ParticipationAllVotesUsed(Exception):
    """The voter has used up all votes for question"""
    pass


class QuestionVoteNotActive(Exception):
    """The question is not active for voting"""
    pass
