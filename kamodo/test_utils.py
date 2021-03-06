from collections import OrderedDict

import numpy as np
import pytest
from sympy import sympify as parse_expr, Symbol
from sympy.core.function import UndefinedFunction

from kamodo import Kamodo
from kamodo.util import kamodofy, gridify, sort_symbols, valid_args, eval_func, get_defaults, cast_0_dim, \
    concat_solution, get_unit_quantity, substr_replace, beautify_latex, arg_to_latex, simulate, symbolic, pad_nan, \
    pointlike, solve, event


@kamodofy
def rho(x=np.array([3, 4, 5])):
    """rho means density"""
    return x ** 2


@kamodofy
def divide(x=np.array([3, 4, 5])):
    """rho means density"""
    return x / 2


@np.vectorize
def myfunc(x, y, z):
    return x + y + z


def defaults_fun(var1, var2, default_var1=10, default_var2=20):
    return var1 + var2 + default_var1 + default_var2


@kamodofy
@gridify(x=np.linspace(-3, 3, 20),
         y=np.linspace(-5, 5, 10),
         z=np.linspace(-7, 7, 30))
def grid_fun(xvec):
    """my density function, returning array of size N

    xvec should have shape (N,3)"""
    return xvec[:, 0]


@pointlike(squeeze='0')
def squeeze_error_point(x=np.linspace(0, 8 * np.pi, 100)):
    return np.sin(x)


@pointlike(squeeze=0)
def squeeze_point(x=np.linspace(0, 8 * np.pi, 100)):
    return np.sin(x)


@pointlike()
def points(x=np.linspace(0, 8 * np.pi, 100)):
    return np.sin(x)


def fprime(x):
    return x * x


@event
def boundry(x, s=np.array([1, 2])):
    r = np.linalg.norm(s)

    if np.isnan(r):
        result = 0
    else:
        result = r - 1
    return result


def test_kamodofy():
    comparison = rho.data == np.array([9, 16, 25])
    assert comparison.all()
    comparison = divide(np.array([6, 13, 2])) == np.array([3, 13 / 2, 1])
    assert comparison.all()


def test_sort_symbols():
    myexpr = parse_expr('x+rho+a+b+c')
    assert sort_symbols(myexpr.free_symbols) == (Symbol('a'), Symbol('b'), Symbol('c'), Symbol('rho'), Symbol('x'))


def test_valid_args():
    assert valid_args(myfunc, dict(x='a', other='you')) == OrderedDict([('x', 'a')])
    assert valid_args(myfunc, dict(y='b', other='you')) == OrderedDict([('y', 'b')])
    assert valid_args(myfunc, dict(z='c', other='you')) == OrderedDict([('z', 'c')])
    assert valid_args(myfunc, dict(x='a', y='b', z='c', other='you')) == OrderedDict(
        [('x', 'a'), ('y', 'b'), ('z', 'c')])


def test_eval_func():
    def f(x):
        return x + 'a'

    with pytest.raises(TypeError) as error:
        eval_func(f, dict(x=1))

    assert eval_func(myfunc, dict(x='a', y='b', z='c', other='you')) == myfunc('a', 'b', 'c')
    assert eval_func(myfunc, dict(x=1, y=2, z=3, other=100)) == myfunc(1, 2, 3)
    assert 'unsupported operand type(s) for +' in str(error)


def test_get_defaults():
    assert get_defaults(defaults_fun) == {'default_var1': 10, 'default_var2': 20}


def test_cast_0_dim():
    to = np.array([1, 2, 3])
    casted_array = cast_0_dim(np.array(1), to=to)
    assert casted_array.shape == to.shape


def test_concat_solution():
    solutions = concat_solution((kamodofy(lambda x=np.array([1, 2, 3]): x ** 2) for i in range(1, 4)), 'y')
    expected = [1, 4, 9, np.nan, 1, 4, 9, np.nan, 1, 4, 9, np.nan, ]
    assert ((solutions['y'] == expected) | (np.isnan(solutions['y']) & np.isnan(expected))).all()


def test_get_unit_quantity():
    from kamodo import get_unit
    mykm = get_unit_quantity('mykm', 'km', scale_factor=2)
    mygm = get_unit_quantity('mygm', 'gram', scale_factor=4)
    assert str(mykm.convert_to(get_unit('m'))) == '2000*meter'
    assert str(mygm.convert_to(get_unit('kg'))) == 'kilogram/250'


def test_substr_replace():
    mystr = "replace this string"
    mystr = substr_replace(mystr, [
        ('this', 'is'),
        ('replace', 'this'),
        ('string', 'replaced')
    ])
    assert mystr == 'this is replaced'


def test_beautify_latex():
    beautified = beautify_latex('LEFTx__plus1RIGHTminusLEFTacommabRIGHT')
    assert beautified == '\\left (x__+1\\right )-\\left (a,b\\right )'


def test_arg_to_latex():
    my_latex = arg_to_latex('x__iplus1')
    assert my_latex == 'x^{i+1}'


def test_simulate():
    def update_y(x):
        return x + 1

    def update_x(y):
        return y - 2

    state_funcs = OrderedDict([
        ('y', update_y),
        ('x', update_x),
        ('t', lambda t, dt: t + dt)
    ])

    simulation = simulate(state_funcs,
                          x=3,  # initial conditions
                          t=0,
                          dt=1,
                          steps=10)

    for state in simulation:
        pass

    assert state['x'] == -7
    assert state['y'] == -5
    assert state['t'] == 10


def test_simulate_error():
    def update_y(x):
        return x + '1'

    def update_x(y):
        return y - 2

    state_funcs = OrderedDict([
        ('y', update_y),
        ('x', update_x),
        ('t', lambda t, dt: t + dt)
    ])

    with pytest.raises(TypeError) as error:
        simulation = simulate(state_funcs,
                              x=3,
                              t=0,
                              dt=1,
                              steps=10)

        for state in simulation:
            pass

    assert "y:unsupported operand type(s) for +" in str(error)


def test_meta_units():
    @kamodofy(units='kg')
    def mass(x):
        return x

    assert mass.meta['units'] == 'kg'


def test_meta_data():
    @kamodofy(units='kg')
    def mass(x=list(range(5)), y=3):
        return [x_ + y for x_ in x]

    assert mass.data[-1] == 7


def test_meta_data_kwargs():
    @kamodofy(x=3, y=3)
    def e(x, y):
        return x + y

    assert e.data == 6

    @kamodofy(x=3)
    def f(x=5, y=3):
        return x + y

    assert f.data == 6

    @kamodofy()
    def g(x, y):
        return x + y

    assert g.data == None
    assert g.meta['units'] == ''

    @kamodofy(data=3)
    def h(x, y):
        return x + y

    assert h.data == 3


def test_repr_latex():
    @kamodofy(equation='$f(x) = x_i^2$')
    def f(x):
        return x

    assert f._repr_latex_() == 'f(x) = x_i^2'

    @kamodofy
    def g(x, y, z):
        return x

    print(g._repr_latex_())

    assert g._repr_latex_() == r'$g{\left(x,y,z \right)} = \lambda{\left(x,y,z \right)}$'


def test_bibtex():
    bibtex = """
@phdthesis{phdthesis,
  author       = {Peter Joslin},
  title        = {The title of the work},
  school       = {The school of the thesis},
  year         = 1993,
  address      = {The address of the publisher},
  month        = 7,
  note         = {An optional note}
}"""

    @kamodofy(citation=bibtex)
    def h(x):
        '''This equation came out of my own brain'''
        return x

    assert '@phdthesis' in h.meta['citation']


def test_gridify():
    from kamodo import Kamodo
    kamodo = Kamodo(grids=grid_fun)
    assert kamodo.grids().shape == (10, 20, 30)


def test_symbolic():
    assert symbolic(['a']) == UndefinedFunction('a')
    assert symbolic(['a', 'b']) == [UndefinedFunction('a'), UndefinedFunction('b')]


def test_pad_nan():
    array = np.array([[1, 2], [1, 2]])
    solution = pad_nan(array)
    expected = np.array([[1, 2], [1, 2], [np.nan, np.nan]])
    comparison = ((solution == expected) | (np.isnan(solution) & np.isnan(expected)))
    assert comparison.all()

    array = np.array([1, 2])
    solution = pad_nan(array)
    expected = np.array([1, 2, np.nan])
    comparison = ((solution == expected) | (np.isnan(solution) & np.isnan(expected)))
    assert comparison.all()

    with pytest.raises(NotImplementedError) as error:
        array = np.array([[[1], [2], [3]], [[1], [2], [3]]])
        pad_nan(array)

    assert f"cannot pad shape {array.shape}" in str(error)


def test_pointlike():
    assert Kamodo(points=squeeze_point).points().shape == (100,)
    assert Kamodo(points=points).points().shape == (1, 100)
    assert Kamodo(points=squeeze_error_point).points().shape == (1, 100)


def test_solve():
    kamodo = Kamodo()
    seeds = np.array([1, 2])
    kamodo['fprime'] = solve(fprime, seeds, 'x', (0, 30), events=boundry)

    assert kamodo.fprime().shape == (2, 2)
