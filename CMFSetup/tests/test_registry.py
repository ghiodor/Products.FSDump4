""" Registry unit tests.

$Id$
"""
import unittest
import os

from Products.CMFSetup.tests.common import BaseRegistryTests

from conformance import ConformsToIStepRegistry
from conformance import ConformsToIImportStepRegistry
from conformance import ConformsToIExportStepRegistry

#==============================================================================
#   Dummy handlers
#==============================================================================
def ONE_FUNC( context ): pass
def TWO_FUNC( context ): pass
def THREE_FUNC( context ): pass
def FOUR_FUNC( context ): pass

ONE_FUNC_NAME = '%s.%s' % ( __name__, ONE_FUNC.__name__ )
TWO_FUNC_NAME = '%s.%s' % ( __name__, TWO_FUNC.__name__ )
THREE_FUNC_NAME = '%s.%s' % ( __name__, THREE_FUNC.__name__ )
FOUR_FUNC_NAME = '%s.%s' % ( __name__, FOUR_FUNC.__name__ )


#==============================================================================
#   SSR tests
#==============================================================================
class ImportStepRegistryTests( BaseRegistryTests
                             , ConformsToIStepRegistry
                             , ConformsToIImportStepRegistry
                             ):

    def _getTargetClass( self ):

        from Products.CMFSetup.registry import ImportStepRegistry
        return ImportStepRegistry

    def test_empty( self ):

        registry = self._makeOne()

        self.assertEqual( len( registry.listSteps() ), 0 )
        self.assertEqual( len( registry.listStepMetadata() ), 0 )
        self.assertEqual( len( registry.sortSteps() ), 0 )

    def test_getStep_nonesuch( self ):

        registry = self._makeOne()

        self.assertEqual( registry.getStep( 'nonesuch' ), None )
        self.assertEqual( registry.getStep( 'nonesuch' ), None )
        default = object()
        self.failUnless( registry.getStepMetadata( 'nonesuch'
                                                 , default ) is default )
        self.failUnless( registry.getStep( 'nonesuch', default ) is default )
        self.failUnless( registry.getStepMetadata( 'nonesuch'
                                                 , default ) is default )

    def test_getStep_defaulted( self ):

        registry = self._makeOne()
        default = object()

        self.failUnless( registry.getStep( 'nonesuch', default ) is default )
        self.assertEqual( registry.getStepMetadata( 'nonesuch', {} ), {} )

    def test_registerStep_docstring( self ):

        def func_with_doc( site ):
            """This is the first line.

            This is the second line.
            """
        FUNC_NAME = '%s.%s' % ( __name__, func_with_doc.__name__ )

        registry = self._makeOne()

        registry.registerStep( id='docstring'
                             , version='1'
                             , handler=func_with_doc
                             , dependencies=()
                             )

        info = registry.getStepMetadata( 'docstring' )
        self.assertEqual( info[ 'id' ], 'docstring' )
        self.assertEqual( info[ 'handler' ], FUNC_NAME )
        self.assertEqual( info[ 'dependencies' ], () )
        self.assertEqual( info[ 'title' ], 'This is the first line.' )
        self.assertEqual( info[ 'description' ] , 'This is the second line.' )

    def test_registerStep_docstring_override( self ):

        def func_with_doc( site ):
            """This is the first line.

            This is the second line.
            """
        FUNC_NAME = '%s.%s' % ( __name__, func_with_doc.__name__ )

        registry = self._makeOne()

        registry.registerStep( id='docstring'
                             , version='1'
                             , handler=func_with_doc
                             , dependencies=()
                             , title='Title'
                             )

        info = registry.getStepMetadata( 'docstring' )
        self.assertEqual( info[ 'id' ], 'docstring' )
        self.assertEqual( info[ 'handler' ], FUNC_NAME )
        self.assertEqual( info[ 'dependencies' ], () )
        self.assertEqual( info[ 'title' ], 'Title' )
        self.assertEqual( info[ 'description' ] , 'This is the second line.' )

    def test_registerStep_single( self ):

        registry = self._makeOne()

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=( 'two', 'three' )
                             , title='One Step'
                             , description='One small step'
                             )

        steps = registry.listSteps()
        self.assertEqual( len( steps ), 1 )
        self.failUnless( 'one' in steps )

        sorted = registry.sortSteps()
        self.assertEqual( len( sorted ), 1 )
        self.assertEqual( sorted[ 0 ], 'one' )

        self.assertEqual( registry.getStep( 'one' ), ONE_FUNC )

        info = registry.getStepMetadata( 'one' )
        self.assertEqual( info[ 'id' ], 'one' )
        self.assertEqual( info[ 'version' ], '1' )
        self.assertEqual( info[ 'handler' ], ONE_FUNC_NAME )
        self.assertEqual( info[ 'dependencies' ], ( 'two', 'three' ) )
        self.assertEqual( info[ 'title' ], 'One Step' )
        self.assertEqual( info[ 'description' ], 'One small step' )

        info_list = registry.listStepMetadata()
        self.assertEqual( len( info_list ), 1 )
        self.assertEqual( info, info_list[ 0 ] )

    def test_registerStep_conflict( self ):

        registry = self._makeOne()

        registry.registerStep( id='one', version='1', handler=ONE_FUNC )

        self.assertRaises( KeyError
                         , registry.registerStep
                         , id='one'
                         , version='0'
                         , handler=ONE_FUNC
                         )

        self.assertRaises( KeyError
                         , registry.registerStep
                         , id='one'
                         , version='1'
                         , handler=ONE_FUNC
                         )

    def test_registerStep_replacement( self ):

        registry = self._makeOne()

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=( 'two', 'three' )
                             , title='One Step'
                             , description='One small step'
                             )

        registry.registerStep( id='one'
                             , version='1.1'
                             , handler=ONE_FUNC
                             , dependencies=()
                             , title='Leads to Another'
                             , description='Another small step'
                             )

        info = registry.getStepMetadata( 'one' )
        self.assertEqual( info[ 'id' ], 'one' )
        self.assertEqual( info[ 'version' ], '1.1' )
        self.assertEqual( info[ 'dependencies' ], () )
        self.assertEqual( info[ 'title' ], 'Leads to Another' )
        self.assertEqual( info[ 'description' ], 'Another small step' )

    def test_registerStep_multiple( self ):

        registry = self._makeOne()

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=()
                             )

        registry.registerStep( id='two'
                             , version='2'
                             , handler=TWO_FUNC
                             , dependencies=()
                             )

        registry.registerStep( id='three'
                             , version='3'
                             , handler=THREE_FUNC
                             , dependencies=()
                             )

        steps = registry.listSteps()
        self.assertEqual( len( steps ), 3 )
        self.failUnless( 'one' in steps )
        self.failUnless( 'two' in steps )
        self.failUnless( 'three' in steps )

    def test_sortStep_simple( self ):

        registry = self._makeOne()

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=( 'two', )
                             )

        registry.registerStep( id='two'
                             , version='2'
                             , handler=TWO_FUNC
                             , dependencies=()
                             )

        steps = registry.sortSteps()
        self.assertEqual( len( steps ), 2 )
        one = steps.index( 'one' )
        two = steps.index( 'two' )

        self.failUnless( 0 <= two < one )

    def test_sortStep_chained( self ):

        registry = self._makeOne()

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=( 'two', )
                             , title='One small step'
                             )

        registry.registerStep( id='two'
                             , version='2'
                             , handler=TWO_FUNC
                             , dependencies=( 'three', )
                             , title='Texas two step'
                             )

        registry.registerStep( id='three'
                             , version='3'
                             , handler=THREE_FUNC
                             , dependencies=()
                             , title='Gimme three steps'
                             )

        steps = registry.sortSteps()
        self.assertEqual( len( steps ), 3 )
        one = steps.index( 'one' )
        two = steps.index( 'two' )
        three = steps.index( 'three' )

        self.failUnless( 0 <= three < two < one )

    def test_sortStep_complex( self ):

        registry = self._makeOne()

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=( 'two', )
                             , title='One small step'
                             )

        registry.registerStep( id='two'
                             , version='2'
                             , handler=TWO_FUNC
                             , dependencies=( 'four', )
                             , title='Texas two step'
                             )

        registry.registerStep( id='three'
                             , version='3'
                             , handler=THREE_FUNC
                             , dependencies=( 'four', )
                             , title='Gimme three steps'
                             )

        registry.registerStep( id='four'
                             , version='4'
                             , handler=FOUR_FUNC
                             , dependencies=()
                             , title='Four step program'
                             )

        steps = registry.sortSteps()
        self.assertEqual( len( steps ), 4 )
        one = steps.index( 'one' )
        two = steps.index( 'two' )
        three = steps.index( 'three' )
        four = steps.index( 'four' )

        self.failUnless( 0 <= four < two < one )
        self.failUnless( 0 <= four < three )

    def test_sortStep_equivalence( self ):

        registry = self._makeOne()

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=( 'two', 'three' )
                             , title='One small step'
                             )

        registry.registerStep( id='two'
                             , version='2'
                             , handler=TWO_FUNC
                             , dependencies=( 'four', )
                             , title='Texas two step'
                             )

        registry.registerStep( id='three'
                             , version='3'
                             , handler=THREE_FUNC
                             , dependencies=( 'four', )
                             , title='Gimme three steps'
                             )

        registry.registerStep( id='four'
                             , version='4'
                             , handler=FOUR_FUNC
                             , dependencies=()
                             , title='Four step program'
                             )

        steps = registry.sortSteps()
        self.assertEqual( len( steps ), 4 )
        one = steps.index( 'one' )
        two = steps.index( 'two' )
        three = steps.index( 'three' )
        four = steps.index( 'four' )

        self.failUnless( 0 <= four < two < one )
        self.failUnless( 0 <= four < three < one )

    def test_checkComplete_simple( self ):

        registry = self._makeOne()

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=( 'two', )
                             )

        incomplete = registry.checkComplete()
        self.assertEqual( len( incomplete ), 1 )
        self.failUnless( ( 'one', 'two' ) in incomplete )

        registry.registerStep( id='two'
                             , version='2'
                             , handler=TWO_FUNC
                             , dependencies=()
                             )

        self.assertEqual( len( registry.checkComplete() ), 0 )

    def test_checkComplete_double( self ):

        registry = self._makeOne()

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=( 'two', 'three' )
                             )

        incomplete = registry.checkComplete()
        self.assertEqual( len( incomplete ), 2 )
        self.failUnless( ( 'one', 'two' ) in incomplete )
        self.failUnless( ( 'one', 'three' ) in incomplete )

        registry.registerStep( id='two'
                             , version='2'
                             , handler=TWO_FUNC
                             , dependencies=()
                             )

        incomplete = registry.checkComplete()
        self.assertEqual( len( incomplete ), 1 )
        self.failUnless( ( 'one', 'three' ) in incomplete )

        registry.registerStep( id='three'
                             , version='3'
                             , handler=THREE_FUNC
                             , dependencies=()
                             )

        self.assertEqual( len( registry.checkComplete() ), 0 )

        registry.registerStep( id='two'
                             , version='2.1'
                             , handler=TWO_FUNC
                             , dependencies=( 'four', )
                             )

        incomplete = registry.checkComplete()
        self.assertEqual( len( incomplete ), 1 )
        self.failUnless( ( 'two', 'four' ) in incomplete )

    def test_generateXML_empty( self ):

        registry = self._makeOne().__of__( self.root )

        xml = registry.generateXML()

        self._compareDOM( registry.generateXML(), _EMPTY_IMPORT_XML )

    def test_generateXML_single( self ):

        registry = self._makeOne().__of__( self.root )

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=()
                             , title='One Step'
                             , description='One small step'
                             )

        self._compareDOM( registry.generateXML(), _SINGLE_IMPORT_XML )

    def test_generateXML_ordered( self ):

        registry = self._makeOne().__of__( self.root )

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=( 'two', )
                             , title='One Step'
                             , description='One small step'
                             )

        registry.registerStep( id='two'
                             , version='2'
                             , handler=TWO_FUNC
                             , dependencies=( 'three', )
                             , title='Two Steps'
                             , description='Texas two step'
                             )

        registry.registerStep( id='three'
                             , version='3'
                             , handler=THREE_FUNC
                             , dependencies=()
                             , title='Three Steps'
                             , description='Gimme three steps'
                             )

        self._compareDOM( registry.generateXML(), _ORDERED_IMPORT_XML )

    def test_parseXML_empty( self ):

        registry = self._makeOne().__of__( self.root )

        registry.registerStep( id='one'
                             , version='1'
                             , handler=ONE_FUNC
                             , dependencies=()
                             , description='One small step'
                             )

        registry.parseXML( _EMPTY_IMPORT_XML )

        self.assertEqual( len( registry.listSteps() ), 0 )
        self.assertEqual( len( registry.listStepMetadata() ), 0 )
        self.assertEqual( len( registry.sortSteps() ), 0 )

    def test_parseXML_single( self ):

        registry = self._makeOne().__of__( self.root )

        registry.registerStep( id='two'
                             , version='2'
                             , handler=TWO_FUNC
                             , dependencies=()
                             , title='Two Steps'
                             , description='Texas two step'
                             )

        registry.parseXML( _SINGLE_IMPORT_XML )

        self.assertEqual( len( registry.listSteps() ), 1 )
        self.failUnless( 'one' in registry.listSteps() )

        info = registry.getStepMetadata( 'one' )
        self.assertEqual( info[ 'id' ], 'one' )
        self.assertEqual( info[ 'version' ], '1' )
        self.assertEqual( info[ 'handler' ], ONE_FUNC_NAME )
        self.assertEqual( info[ 'dependencies' ], () )
        self.assertEqual( info[ 'title' ], 'One Step' )
        self.failUnless( 'One small step' in info[ 'description' ] )

    def test_parseXML_ordered( self ):

        registry = self._makeOne().__of__( self.root )

        registry.parseXML( _ORDERED_IMPORT_XML )

        self.assertEqual( len( registry.listSteps() ), 3 )
        self.failUnless( 'one' in registry.listSteps() )
        self.failUnless( 'two' in registry.listSteps() )
        self.failUnless( 'three' in registry.listSteps() )

        steps = registry.sortSteps()
        self.assertEqual( len( steps ), 3 )
        one = steps.index( 'one' )
        two = steps.index( 'two' )
        three = steps.index( 'three' )

        self.failUnless( 0 <= three < two < one )


_EMPTY_IMPORT_XML = """\
<?xml version="1.0"?>
<import-steps>
</import-steps>
"""

_SINGLE_IMPORT_XML = """\
<?xml version="1.0"?>
<import-steps>
 <import-step id="one"
             version="1"
             handler="%s"
             title="One Step">
  One small step
 </import-step>
</import-steps>
""" % ( ONE_FUNC_NAME, )

_ORDERED_IMPORT_XML = """\
<?xml version="1.0"?>
<import-steps>
 <import-step id="one"
             version="1"
             handler="%s"
             title="One Step">
  <dependency step="two" />
  One small step
 </import-step>
 <import-step id="three"
             version="3"
             handler="%s"
             title="Three Steps">
  Gimme three steps
 </import-step>
 <import-step id="two"
             version="2"
             handler="%s"
             title="Two Steps">
  <dependency step="three" />
  Texas two step
 </import-step>
</import-steps>
""" % ( ONE_FUNC_NAME, THREE_FUNC_NAME, TWO_FUNC_NAME )


#==============================================================================
#   ESR tests
#==============================================================================
class ExportStepRegistryTests( BaseRegistryTests
                             , ConformsToIStepRegistry
                             , ConformsToIExportStepRegistry
                             ):

    def _getTargetClass( self ):

        from Products.CMFSetup.registry import ExportStepRegistry
        return ExportStepRegistry

    def _makeOne( self, *args, **kw ):

        return self._getTargetClass()( *args, **kw )

    def test_empty( self ):

        registry = self._makeOne()
        self.assertEqual( len( registry.listSteps() ), 0 )
        self.assertEqual( len( registry.listStepMetadata() ), 0 )

    def test_getStep_nonesuch( self ):

        registry = self._makeOne()
        self.assertEqual( registry.getStep( 'nonesuch' ), None )

    def test_getStep_defaulted( self ):

        registry = self._makeOne()
        default = lambda x: false
        self.assertEqual( registry.getStep( 'nonesuch', default ), default )

    def test_getStepMetadata_nonesuch( self ):

        registry = self._makeOne()
        self.assertEqual( registry.getStepMetadata( 'nonesuch' ), None )

    def test_getStepMetadata_defaulted( self ):

        registry = self._makeOne()
        self.assertEqual( registry.getStepMetadata( 'nonesuch', {} ), {} )

    def test_registerStep_simple( self ):

        registry = self._makeOne()
        registry.registerStep( 'one', ONE_FUNC )
        info = registry.getStepMetadata( 'one', {} )

        self.assertEqual( info[ 'id' ], 'one' )
        self.assertEqual( info[ 'handler' ], ONE_FUNC_NAME )
        self.assertEqual( info[ 'title' ], 'one' )
        self.assertEqual( info[ 'description' ], '' )

    def test_registerStep_docstring( self ):

        def func_with_doc( site ):
            """This is the first line.

            This is the second line.
            """
        FUNC_NAME = '%s.%s' % ( __name__, func_with_doc.__name__ )

        registry = self._makeOne()
        registry.registerStep( 'one', func_with_doc )
        info = registry.getStepMetadata( 'one', {} )

        self.assertEqual( info[ 'id' ], 'one' )
        self.assertEqual( info[ 'handler' ], FUNC_NAME )
        self.assertEqual( info[ 'title' ], 'This is the first line.' )
        self.assertEqual( info[ 'description' ] , 'This is the second line.' )

    def test_registerStep_docstring_with_override( self ):

        def func_with_doc( site ):
            """This is the first line.

            This is the second line.
            """
        FUNC_NAME = '%s.%s' % ( __name__, func_with_doc.__name__ )

        registry = self._makeOne()
        registry.registerStep( 'one', func_with_doc
                               , description='Description' )
        info = registry.getStepMetadata( 'one', {} )

        self.assertEqual( info[ 'id' ], 'one' )
        self.assertEqual( info[ 'handler' ], FUNC_NAME )
        self.assertEqual( info[ 'title' ], 'This is the first line.' )
        self.assertEqual( info[ 'description' ], 'Description' )

    def test_registerStep_collision( self ):

        registry = self._makeOne()
        registry.registerStep( 'one', ONE_FUNC )
        self.assertRaises( KeyError, registry.registerStep, 'one', TWO_FUNC )

    def test_generateXML_empty( self ):

        registry = self._makeOne().__of__( self.root )

        xml = registry.generateXML()

        self._compareDOM( registry.generateXML(), _EMPTY_EXPORT_XML )

    def test_generateXML_single( self ):

        registry = self._makeOne().__of__( self.root )

        registry.registerStep( id='one'
                             , handler=ONE_FUNC
                             , title='One Step'
                             , description='One small step'
                             )

        self._compareDOM( registry.generateXML(), _SINGLE_EXPORT_XML )

    def test_generateXML_ordered( self ):

        registry = self._makeOne().__of__( self.root )

        registry.registerStep( id='one'
                             , handler=ONE_FUNC
                             , title='One Step'
                             , description='One small step'
                             )

        registry.registerStep( id='two'
                             , handler=TWO_FUNC
                             , title='Two Steps'
                             , description='Texas two step'
                             )

        registry.registerStep( id='three'
                             , handler=THREE_FUNC
                             , title='Three Steps'
                             , description='Gimme three steps'
                             )

        self._compareDOM( registry.generateXML(), _ORDERED_EXPORT_XML )

    def test_parseXML_empty( self ):

        registry = self._makeOne().__of__( self.root )

        registry.registerStep( id='one'
                             , handler=ONE_FUNC
                             , description='One small step'
                             )

        registry.parseXML( _EMPTY_EXPORT_XML )

        self.assertEqual( len( registry.listSteps() ), 0 )
        self.assertEqual( len( registry.listStepMetadata() ), 0 )

    def test_parseXML_single( self ):

        registry = self._makeOne().__of__( self.root )

        registry.registerStep( id='two'
                             , handler=TWO_FUNC
                             , title='Two Steps'
                             , description='Texas two step'
                             )

        registry.parseXML( _SINGLE_EXPORT_XML )

        self.assertEqual( len( registry.listSteps() ), 1 )
        self.failUnless( 'one' in registry.listSteps() )

        info = registry.getStepMetadata( 'one' )
        self.assertEqual( info[ 'id' ], 'one' )
        self.assertEqual( info[ 'handler' ], ONE_FUNC_NAME )
        self.assertEqual( info[ 'title' ], 'One Step' )
        self.failUnless( 'One small step' in info[ 'description' ] )

    def test_parseXML_single_as_ascii( self ):

        registry = self._makeOne().__of__( self.root )

        registry.registerStep( id='two'
                             , handler=TWO_FUNC
                             , title='Two Steps'
                             , description='Texas two step'
                             )

        registry.parseXML( _SINGLE_EXPORT_XML, encoding='ascii' )

        self.assertEqual( len( registry.listSteps() ), 1 )
        self.failUnless( 'one' in registry.listSteps() )

        info = registry.getStepMetadata( 'one' )
        self.assertEqual( info[ 'id' ], 'one' )
        self.assertEqual( info[ 'handler' ], ONE_FUNC_NAME )
        self.assertEqual( info[ 'title' ], 'One Step' )
        self.failUnless( 'One small step' in info[ 'description' ] )

    def test_parseXML_ordered( self ):

        registry = self._makeOne().__of__( self.root )

        registry.parseXML( _ORDERED_EXPORT_XML )

        self.assertEqual( len( registry.listSteps() ), 3 )
        self.failUnless( 'one' in registry.listSteps() )
        self.failUnless( 'two' in registry.listSteps() )
        self.failUnless( 'three' in registry.listSteps() )


_EMPTY_EXPORT_XML = """\
<?xml version="1.0"?>
<export-steps>
</export-steps>
"""

_SINGLE_EXPORT_XML = """\
<?xml version="1.0"?>
<export-steps>
 <export-step id="one"
                handler="%s"
                title="One Step">
  One small step
 </export-step>
</export-steps>
""" % ( ONE_FUNC_NAME, )

_ORDERED_EXPORT_XML = """\
<?xml version="1.0"?>
<export-steps>
 <export-step id="one"
                handler="%s"
                title="One Step">
  One small step
 </export-step>
 <export-step id="three"
                handler="%s"
                title="Three Steps">
  Gimme three steps
 </export-step>
 <export-step id="two"
                handler="%s"
                title="Two Steps">
  Texas two step
 </export-step>
</export-steps>
""" % ( ONE_FUNC_NAME, THREE_FUNC_NAME, TWO_FUNC_NAME )


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite( ImportStepRegistryTests ),
        unittest.makeSuite( ExportStepRegistryTests ),
        ))

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')