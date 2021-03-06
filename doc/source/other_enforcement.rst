.. _other-enforcement:

Other Enforcement Techniques
============================

Congress's policy language was designed to balance the needs of the people who write complex policies (e.g. encoding the relevant fragments of HIPAA) and the needs of the software that enforces that policy.  Too rich a policy language and the software cannot properly enforce it; too poor and people cannot write the policy they care about.

Because the policy language is less expressive than a traditional programming languages, there will undoubtedly arise situations where we need to hit Congress with a hammer.  There are several ways to do that.

- Create your own cloud service
- Write the enforcement policy
- Access control policy (unimplemented)




* Write a separate *Action Description* policy that describes how each of the API calls (which we call *actions*) change the state of the cloud.  Congress can then be asked to :func:`simulate` the effects of any action and check if an action execution would cause any new policy violations.  External cloud services like Nova and Heat can then more directly pose the question of whether or not a given API call should be rejected.

If the cloud and policy are such that all potential violations can be prevented before they occur, the Access Control policy approach is the right one, and the policy described in :ref:`policy` (called the *Classification policy*) is unnecessary because it will never be violated.  But if there is ever a time at which some fragment of the policy might be violated, the Action-description approach is superior.  Instead of writing two separate policies (the Classification policy and the Access Control policy) that have similar contents, we write two separate policies that have almost entirely independent contents (the Classification policy and the Action policy).

<Action description language>

<inserting action description policy into Congress>




Customizing Enforcement
-------------------------
- can choose which cloud services to make consult Congress before taking action.
- can choose which actions to make available in the Action policy
- can change condition-action rules in the Enforcement policy.
- can change the Access Control Policy

