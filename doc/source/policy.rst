.. include:: aliases.rst

.. _policy:

======
Policy
======

1. What Does a Policy Look Like
===============================

A policy describes how services (either individually or as a whole)
ought to behave.  More specifically, a policy describes which
**states** of the cloud are permitted and which are not.  For example,
a policy that requires all systems to enforce a minimum password
length of eight characters would flag a service that has a minimum
password length of six.

The state of the cloud is the amalgamation of the states of all the
services running in the cloud.  In Congress, the state of each service
is represented as a collection of tables (see :ref:`cloudservices`, ).
The policy language determines whether any violation exists given the
content of the state tables.

For example, one desirable policy is that each Neutron port has at
most one IP address.  That means that the following table mapping port
id to ip address with the schema "port(id, ip)" is permitted by the
policy.

====================================== ==========
ID                                     IP
====================================== ==========
"66dafde0-a49c-11e3-be40-425861b86ab6" "10.0.0.1"
"73e31d4c-e89b-12d3-a456-426655440000" "10.0.0.3"
====================================== ==========

Whereas, the following table is a violation.

====================================== ==========
ID                                     IP
====================================== ==========
"66dafde0-a49c-11e3-be40-425861b86ab6" "10.0.0.1"
"66dafde0-a49c-11e3-be40-425861b86ab6" "10.0.0.2"
"73e31d4c-e89b-12d3-a456-426655440000" "10.0.0.3"
====================================== ==========

This is the policy written in Congress's policy language:

error(port_id, ip1, ip2) :-
  port(port_id, ip1),
  port(port_id, ip2),
  not equal(ip1, ip2);

Note that the policy above does not mention specific table content;
instead it describes the general condition of tables.  The policy says
that for every row in the port table, no two rows should have the same
ID and different IPs.

This example verifies a single table within Neutron, but a
policy can use many tables as well.  Those tables
might all come from the same cloud service (e.g. all the tables might be
Neutron tables), or the tables may come from different cloud services (e.g.
some tables from Neutron, others from Nova).

For example, if we have the following table schemas from Nova, Neutron, and
|ad|, we could write a policy that says every network connected to a VM must
either be public or owned by someone in the same group as the VM owner.::

  error(vm) :-
    nova:virtual_machine(vm)
    nova:network(vm, network)
    nova:owner(vm, vm_owner)
    neutron:owner(network, network_owner)
    not neutron:public_network(network)
    not same_group(vm_owner, network_owner)

  same_group(user1, user2) :-
    ad:group(user1, group)
    ad:group(user2, group)

This example illustrates the need for a rich language to describe which
combinations of
tables are permitted and which are not.  The basic language Congress supports
for expressing policy is called Datalog, a declarative language derived from
SQL and first-order logic that has existed for decades.

The rest of this chapter describes the policy language Congress uses,
and how to write policies in more detail.


.. _datalog:

2. Datalog Policy Language
==========================

Conceptually, Datalog is a language for (i) describing invariants that tables
should always obey, (ii) defining new tables from existing tables, (iii)
describing existing tables.  The policy that describes how the cloud should
behave is a collection of Datalog invariants dictating which combinations of
tables are permitted and which are prohibited.  For example, we might want
every VM connected to a network to be a member of the "secure" security group.
This invariant describes which states of the cloud are permitted and which
states are not.

When writing invariants, it is often useful to use higher-level concepts than
the cloud services provide natively.  Datalog allows us to do this by defining
new tables (higher-level concepts) in terms of existing tables (lower-level
concepts) by writing *rules*.  For example, OpenStack does not tell us directly
which VMs are connected to the internet; rather, it provides a collection of
lower-level API calls from which we can derive that information.  Using Datalog
we can define a table that lists all of the VMs connected to the internet in
terms of the tables that Nova/Neutron support directly.  For example, if
Keystone stores some collection of user groups and Active Directory stores a
collection of user groups, we might want to create a new table that represents
all the groups from either Keystone or Active Directory.

Datalog also allows us to represent concrete tables directly in the language.
This is useful mainly because it makes it easy to experiment with and
understand rules and invariants.

In what follows we explain how to use each of the main features of Datalog.

**Concrete tables.**  Suppose we want to use Datalog to represent a Neutron
table that lists which ports have been assigned which IPs, such as the one
shown below.

Table: neutron:port_ip

====================================== ==========
ID                                     IP
====================================== ==========
"66dafde0-a49c-11e3-be40-425861b86ab6" "10.0.0.1"
"66dafde0-a49c-11e3-be40-425861b86ab6" "10.0.0.2"
"73e31d4c-e89b-12d3-a456-426655440000" "10.0.0.3"
====================================== ==========

To represent this table, we would write the following Datalog::

    neutron:port_ip("66dafde0-a49c-11e3-be40-425861b86ab6", "10.0.0.1")
    neutron:port_ip("66dafde0-a49c-11e3-be40-425861b86ab6", "10.0.0.2")
    neutron:port_ip("73e31d4c-e89b-12d3-a456-426655440000", "10.0.0.3")

Each of the Datalog statements above is called a *ground atom* (or *ground
fact*).  A ground atom takes the form ``<tablename>(arg1, ..., argn)``,
where each ``argi`` is either a double-quoted Python string or a Python
number.

**Basic rules** Besides describing specific instances of tables, Datalog
allows us to describe recipes for how to construct new tables out of existing
tables, regardless which rows are in those existing tables.

To create a new table out of an existing table, we write Datalog *rules*.
A *rule* is a simple if-then statement, where the *if* part is called the
*head* and the *then* part is called the *body*.  The head is always a single
Datalog atom.  The body is an AND of several possibly negated Datalog atoms.
OR is accomplished by writing multiple rules with the same table in the head.

Suppose we want to create a new table ``has_ip`` that is just a list of
the Neutron ports that have been assigned at least one IP address.  We want
our table to work regardless what IDs and IPs appear in the neutron:port_ip
table so we use variables in place of strings/numbers.  Variables have the
same meaning as in algebra: they are placeholders for any value.
(Syntactically, a variable is any symbol other than a number or a string.)::

    has_ip(x) :- neutron:port_ip(x, y)

This rule says that a port *x* belongs to the *has_ip* table if there exists
some IP *y* such that row *<x,y>* belongs to the *neutron:port* table.
Conceptually, this rule says to look at all of the ground atoms for the
neutron:port_ip table, and for each one assign *x* to the port UUID and *y*
to the IP.  Then create a row in the *has_ip* table for *x*.  This rule when
applied to the neutron:port_ip table shown above would generate the following
table::

    has_ip("66dafde0-a49c-11e3-be40-425861b86ab6")
    has_ip("73e31d4c-e89b-12d3-a456-426655440000")

Notice here that there are only 2 rows in *has_ip* despite there being 3 rows
in *neutron:port_ip*.  That happens because one of the ports in
neutron:port_ip has been assigned 2 distinct IPs.

**AND operator** As a slightly more complex example, we could define a table
*same_ip* that lists all the pairs of ports that are assigned the same IP.::

    same_ip(port1, port2) :- neutron:port_ip(port1, ip), neutron:port(port2, ip)

In this case we use multiple atoms in the body of the rule.  We use the same
variable *ip* in both tables (called a *join* for those of you familiar with
relational databases and SQL).  The pair <port1, port2> is included in
*same_ip* if there exists some *ip* where both *<port1, ip>* and *<port2, ip>*
both belong to the *neutron:port* table and the value assigned to the variable
*ip* is the same in both cases.

**NOT operator** As another example, suppose we want a list of all the ports
that have NOT been assigned IP addresses.  We can use the *not* operator to
check if a row fails to belong to a table.

    no_ip(port) :- neutron:port(port), not has_ip(port)

There are special restrictions that you must be aware of when using *not*.
See the next section for details.

**OR operator**. Some examples require an OR, which in Datalog means writing
multiple rules with the same table in the head.   Imagine we have two tables
representing group membership information from two different services:
Keystone and Active Directory.  We can create a new table *group* that says a
person is a member of a group if she is a member of that group either according
to Keystone or according to Active Directory.  In Datalog we create this table
by writing two rules.::

    group(user, grp) :- ad:group(user, grp)
    group(user, grp) :- keystone:group(user, grp)

These rules happen to have only one atom in each of their bodies, but there is
no requirement for that.

**Builtins**. Often we want to write rules that are conditioned on things that
are difficult or impossible to define within Datalog.  For example, we might
want to create a table that lists all of the virtual machines that have at
least 100 GB of memory.  Arithmetic, string manipulation, etc. are operations
that we define outside of Datalog using traditional (Python) code.  Datalog
engine developers provide a number of these *builtins*, such as the
*greater_than* table shown below.

    plenty_of_memory(vm) :- nova:virtual_machine.memory(vm, mem), greater_than(mem, 100)

**Table hierarchy**.   The tables in the body of rules can either be the
original cloud-service tables or tables that are defined by other rules
(with some limitations, described in the next section).  We can think of a
Datalog policy as a hierarchy of tables, where each table is defined in
terms of the tables at a lower level in the hierarchy.  At the bottom of that
hierarchy are the original cloud-service tables representing the state of the
cloud.

**Order irrelevance**.  One noteworthy feature of Datalog is that the order
in which rules appear is irrelevant.  The rows that belong to a table are
the minimal ones required by the rules if we were to compute their contents
starting with the cloud-service tables (whose contents are given to us) and
working our way up the hierarchy of tables.  For more details, search the web
for the term *stratified Datalog semantics*.

Here is the grammar for Datalog policies::

    <policy> ::= <rule>*
    <rule> ::= <atom> COLONMINUS <literal> (COMMA <literal>)*
    <literal> ::= <atom>
    <literal> ::= NOT <atom>
    <atom> ::= TABLENAME LPAREN <term> (COMMA <term>)* RPAREN
    <term> ::= INTEGER | FLOAT | STRING | VARIABLE


2.1 Datalog Syntax Restrictions
-------------------------------

There are a number of syntactic restrictions on Datalog that are, for the most
part, common sense.

**Head Safety**
    every variable in the head of a rule must appear in the body.

Head Safety is natural because if a variable appears in the head of the rule
but not the body, we have not given a prescription for which constants
(strings/numbers) to use for that variable.

**Body Safety**
    every variable in a negated atom or in a built-in table must appear in a
    non-negated, non-builtin atom in the body.

Body Safety is important for ensuring that the sizes of our tables are always
finite.  There are always infinitely many rows that DO NOT belong to a table,
and there are often infinitely many rows that DO belong to a builtin
(like equal).  For some builtin tables, the Body Safety restriction is overly
strong, but having the restriction in place ensures that the Datalog engine
can treat all built-in tables the same.

.. **Stratification [Recursion is not currently supported]**
..    No table may be defined in terms of its negation.

.. In Datalog, a table may be defined in terms of itself.  These are called
   *recursive* tables.  A classic example is defining all pairs of nodes that
   are connected in a network given a table that records which nodes are adjacent
   to which other nodes (i.e. by a single network hop).::

..    connected(x,y) :- adjacent(x,y)
..    connected(x,y) :- connected(x,z), connected(z,y)

.. The Stratification restriction says that we cannot define a table in terms of
   its *negation*.  For example, the following rule is disallowed.::

..    p(x) :- not p(x)   // NOT valid Datalog

.. More precisely, the Stratification restriction says that there is no cycle
   through the dependency graph of a Datalog policy that includes an edge
   labeled with *negation*.  The dependency graph of a Datalog policy has
   one node for every table.  It has an edge from table u to table v if
   there is a rule with u in the head and v in the body; that edge is labeled
   with *negation* if NOT is applied to the atom for v.

3. Invariants and Policy
========================

We began by saying that a Congress policy dictates which
combinations of tables are permitted and which are prohibited--which
invariants must be true over the tables representing the state of the
cloud.
Invariants in Datalog are written as a special kind of rule: a rule with
the ``error`` table in the head.  Any row that belongs to the error
table represents an invariant--a violation of policy.

Recall the two example policies from Section 1, for port/ip addresses
and public/same_group networking.  In those examples, the policy rules
populate the error table when a port or VM violates the policy.  Also note
that while Datalog reserves the ``error`` tablename, it puts no restrictions
on what the columns of the error table represent.  In fact, different rules
can use different numbers of columns.

In summary, a Congress policy is a collection of Datalog rules.  When those
rules are evaluated over the tables representing the current state of the
cloud, any row appearing in the ``error`` table indicates a policy
violation.

