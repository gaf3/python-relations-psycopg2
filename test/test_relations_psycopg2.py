import unittest
import unittest.mock

import os
import psycopg2.extras

import relations
import relations_psycopg2

class SourceModel(relations.Model):
    SOURCE = "PsycoPg2Source"

class Simple(SourceModel):
    id = int
    name = str

class Plain(SourceModel):
    ID = None
    simple_id = int
    name = str

relations.OneToMany(Simple, Plain)

class Unit(SourceModel):
    id = int
    name = str

class Test(SourceModel):
    id = int
    unit_id = int
    name = str

class Case(SourceModel):
    id = int
    test_id = int
    name = str

relations.OneToMany(Unit, Test)
relations.OneToOne(Test, Case)

class TestSource(unittest.TestCase):

    maxDiff = None

    def setUp(self):

        self.connection = psycopg2.connect(
            user="postgres", host=os.environ["POSTGRES_HOST"], port=int(os.environ["POSTGRES_PORT"]),
            cursor_factory=psycopg2.extras.RealDictCursor
        )

        self.connection.autocommit = True

        cursor = self.connection.cursor()
        cursor.execute('DROP DATABASE IF EXISTS "test_source"')
        cursor.execute('CREATE DATABASE "test_source"')

        self.source = relations_psycopg2.Source(
            "PsycoPg2Source", "test_source", user="postgres", host=os.environ["POSTGRES_HOST"], port=int(os.environ["POSTGRES_PORT"])
        )

    def tearDown(self):

        self.source.connection.close()

        cursor = self.connection.cursor()
        cursor.execute('DROP DATABASE "test_source"')
        self.connection.close()

    @unittest.mock.patch("relations.SOURCES", {})
    @unittest.mock.patch("psycopg2.connect", unittest.mock.MagicMock())
    def test___init__(self):

        source = relations_psycopg2.Source("unit", "init", connection="corkneckshurn")
        self.assertFalse(source.created)
        self.assertEqual(source.name, "unit")
        self.assertEqual(source.database, "init")
        self.assertIsNone(source.schema)
        self.assertEqual(source.connection, "corkneckshurn")
        self.assertEqual(relations.SOURCES["unit"], source)

        source = relations_psycopg2.Source("test", "init", schema="private", extra="stuff")
        self.assertTrue(source.created)
        self.assertEqual(source.name, "test")
        self.assertEqual(source.database, "init")
        self.assertEqual(source.schema, "private")
        self.assertEqual(source.connection, psycopg2.connect.return_value)
        self.assertEqual(relations.SOURCES["test"], source)
        psycopg2.connect.assert_called_once_with(cursor_factory=psycopg2.extras.RealDictCursor, dbname="init", extra="stuff")

    @unittest.mock.patch("relations.SOURCES", {})
    @unittest.mock.patch("psycopg2.connect", unittest.mock.MagicMock())
    def test___del__(self):

        relations_psycopg2.Source("test", "init", schema="private", extra="stuff")
        del relations.SOURCES["test"]
        psycopg2.connect.return_value.close.assert_called_once_with()

    def test_table(self):

        model = unittest.mock.MagicMock()
        model.SCHEMA = None

        self.source.schema = "public"
        model.TABLE = "people"
        self.assertEqual(self.source.table(model), '"public"."people"')

        model.SCHEMA = "things"
        self.assertEqual(self.source.table(model), '"things"."people"')

    def test_field_init(self):

        class Field:
            pass

        field = Field()

        self.source.field_init(field)

        self.assertIsNone(field.primary_key)
        self.assertIsNone(field.serial)
        self.assertIsNone(field.definition)

    def test_model_init(self):

        class Check(relations.Model):
            id = int
            name = str

        model = Check()

        self.source.model_init(model)

        self.assertIsNone(model.DATABASE)
        self.assertIsNone(model.SCHEMA)
        self.assertEqual(model.TABLE, "check")
        self.assertEqual(model.QUERY.get(), 'SELECT * FROM "check"')
        self.assertIsNone(model.DEFINITION)
        self.assertTrue(model._fields._names["id"].primary_key)
        self.assertTrue(model._fields._names["id"].serial)
        self.assertTrue(model._fields._names["id"].readonly)

    def test_field_define(self):

        # Specific

        field = relations.Field(int, definition='id')
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['id'])

        # INT

        field = relations.Field(int, store='_id')
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['"_id" INT'])

        # INT default

        field = relations.Field(int, store='_id', default=0)
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['"_id" INT NOT NULL DEFAULT 0'])

        # INT none

        field = relations.Field(int, store='_id', none=False)
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['"_id" INT NOT NULL'])

        # INT primary

        field = relations.Field(int, store='_id', primary_key=True)
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['"_id" INT PRIMARY KEY'])

        # INT full

        field = relations.Field(int, store='_id', none=False, primary_key=True, serial=True)
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['"_id" SERIAL NOT NULL PRIMARY KEY'])

        # VARCHAR

        field = relations.Field(str, name='name')
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['"name" VARCHAR(255)'])

        # VARCHAR length

        field = relations.Field(str, name='name', length=32)
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['"name" VARCHAR(32)'])

        # VARCHAR default

        field = relations.Field(str, name='name', default='ya')
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['"name" VARCHAR(255) NOT NULL DEFAULT \'ya\''])

        # VARCHAR none

        field = relations.Field(str, name='name', none=False)
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['"name" VARCHAR(255) NOT NULL'])

        # VARCHAR full

        field = relations.Field(str, name='name', length=32, none=False, default='ya')
        self.source.field_init(field)
        definitions = []
        self.source.field_define(field, definitions)
        self.assertEqual(definitions, ['"name" VARCHAR(32) NOT NULL DEFAULT \'ya\''])

    def test_model_define(self):

        class Simple(relations.Model):

            SOURCE = "PsycoPg2Source"
            DEFINITION = "whatever"

            id = int
            name = str

            INDEX = "id"

        self.assertEqual(Simple.define(), "whatever")

        Simple.DEFINITION = None
        self.assertEqual(Simple.define(), [
            """CREATE TABLE IF NOT EXISTS "simple" (
  "id" SERIAL PRIMARY KEY,
  "name" VARCHAR(255)
)""",
            """CREATE UNIQUE INDEX "name" ON "simple" ("name")""",
            """CREATE INDEX "id" ON "simple" ("id")"""
        ])

        cursor = self.source.connection.cursor()
        [cursor.execute(statement) for statement in Simple.define()]
        cursor.close()

    def test_field_create(self):

        # Standard

        field = relations.Field(int, name="id")
        self.source.field_init(field)
        fields = []
        clause = []
        self.source.field_create( field, fields, clause)
        self.assertEqual(fields, ['"id"'])
        self.assertEqual(clause, ["%(id)s"])
        self.assertFalse(field.changed)

        # readonly

        field = relations.Field(int, name="id", readonly=True)
        self.source.field_init(field)
        fields = []
        clause = []
        self.source.field_create( field, fields, clause)
        self.assertEqual(fields, [])
        self.assertEqual(clause, [])

    def test_model_create(self):

        simple = Simple("sure")
        simple.plain.add("fine")

        cursor = self.source.connection.cursor()
        [cursor.execute(statement) for statement in Simple.define() + Plain.define()]

        simple.create()

        self.assertEqual(simple._action, "update")
        self.assertEqual(simple._record._action, "update")
        self.assertEqual(simple.plain[0].simple_id, simple.id)
        self.assertEqual(simple.plain._action, "update")
        self.assertEqual(simple.plain[0]._record._action, "update")

        cursor.execute("SELECT * FROM simple")
        self.assertEqual(cursor.fetchone(), {"id": 1, "name": "sure"})

        cursor.execute("SELECT * FROM plain")
        self.assertEqual(cursor.fetchone(), {"simple_id": 1, "name": "fine"})

        cursor.close()

    def test_field_retrieve(self):

        # IN

        field = relations.Field(int, name='id')
        self.source.field_init(field)
        field.filter([1, 2, 3], 'in')
        query = relations.query.Query()
        values = []
        self.source.field_retrieve( field, query, values)
        self.assertEqual(query.wheres, '"id" IN (%s,%s,%s)')
        self.assertEqual(values, [1, 2, 3])

        # NOT IN

        field = relations.Field(int, name='id')
        self.source.field_init(field)
        field.filter([1, 2, 3], 'ne')
        query = relations.query.Query()
        values = []
        self.source.field_retrieve( field, query, values)
        self.assertEqual(query.wheres, '"id" NOT IN (%s,%s,%s)')
        self.assertEqual(values, [1, 2, 3])

        # =

        field = relations.Field(int, name='id')
        self.source.field_init(field)
        field.filter(1)
        query = relations.query.Query()
        values = []
        self.source.field_retrieve( field, query, values)
        self.assertEqual(query.wheres, '"id"=%s')
        self.assertEqual(values, [1])

        # >

        field = relations.Field(int, name='id')
        self.source.field_init(field)
        field.filter(1, 'gt')
        query = relations.query.Query()
        values = []
        self.source.field_retrieve( field, query, values)
        self.assertEqual(query.wheres, '"id">%s')
        self.assertEqual(values, [1])

        # >=

        field = relations.Field(int, name='id')
        self.source.field_init(field)
        field.filter(1, 'ge')
        query = relations.query.Query()
        values = []
        self.source.field_retrieve( field, query, values)
        self.assertEqual(query.wheres, '"id">=%s')
        self.assertEqual(values, [1])

        # <

        field = relations.Field(int, name='id')
        self.source.field_init(field)
        field.filter(1, 'lt')
        query = relations.query.Query()
        values = []
        self.source.field_retrieve( field, query, values)
        self.assertEqual(query.wheres, '"id"<%s')
        self.assertEqual(values, [1])

        # <=

        field = relations.Field(int, name='id')
        self.source.field_init(field)
        field.filter(1, 'le')
        query = relations.query.Query()
        values = []
        self.source.field_retrieve( field, query, values)
        self.assertEqual(query.wheres, '"id"<=%s')
        self.assertEqual(values, [1])

    def test_model_retrieve(self):

        model = Unit()

        cursor = self.source.connection.cursor()

        [cursor.execute(statement) for statement in Unit.define() + Test.define() + Case.define()]

        Unit([["people"], ["stuff"]]).create()

        models = Unit.one(name__in=["people", "stuff"])
        self.assertRaisesRegex(relations.ModelError, "unit: more than one retrieved", models.retrieve)

        model = Unit.one(name="things")
        self.assertRaisesRegex(relations.ModelError, "unit: none retrieved", model.retrieve)

        self.assertIsNone(model.retrieve(False))

        unit = Unit.one(name="people")

        self.assertEqual(unit.id, 1)
        self.assertEqual(unit._action, "update")
        self.assertEqual(unit._record._action, "update")

        unit.test.add("things")[0].case.add("persons")
        unit.update()

        model = Unit.many(test__name="things")

        self.assertEqual(model.id, [1])
        self.assertEqual(model[0]._action, "update")
        self.assertEqual(model[0]._record._action, "update")
        self.assertEqual(model[0].test[0].id, 1)
        self.assertEqual(model[0].test[0].case.name, "persons")

    def test_field_update(self):

        # Standard

        field = relations.Field(int, name="id")
        self.source.field_init(field)
        clause = []
        values = []
        field.value = 1
        self.source.field_update(field, clause, values)
        self.assertEqual(clause, ['"id"=%s'])
        self.assertEqual(values, [1])
        self.assertFalse(field.changed)

        # not changed

        clause = []
        values = []
        self.source.field_update(field, clause, values, changed=True)
        self.assertEqual(clause, [])
        self.assertEqual(values, [])
        self.assertFalse(field.changed)

        # readonly

        field = relations.Field(int, name="id", readonly=True)
        self.source.field_init(field)
        clause = []
        values = []
        field.value = 1
        self.source.field_update( field, clause, values)
        self.assertEqual(clause, [])
        self.assertEqual(values, [])

    def test_model_update(self):

        cursor = self.source.connection.cursor()

        [cursor.execute(statement) for statement in Unit.define() + Test.define() + Case.define()]

        Unit([["people"], ["stuff"]]).create()

        unit = Unit.many(id=2).set(name="things")

        self.assertEqual(unit.update(), 1)

        unit = Unit.one(2)

        unit.name = "thing"
        unit.test.add("moar")

        self.assertEqual(unit.update(), 1)
        self.assertEqual(unit.name, "thing")
        self.assertEqual(unit.test[0].unit_id, unit.id)
        self.assertEqual(unit.test[0].name, "moar")

        plain = Plain.one()
        self.assertRaisesRegex(relations.ModelError, "plain: nothing to update from", plain.update)

    def test_model_delete(self):

        cursor = self.source.connection.cursor()

        [cursor.execute(statement) for statement in Unit.define() + Test.define() + Case.define()]

        unit = Unit("people")
        unit.test.add("stuff").add("things")
        unit.create()

        self.assertEqual(Test.one(id=2).delete(), 1)
        self.assertEqual(len(Test.many()), 1)

        self.assertEqual(Unit.one(1).test.delete(), 1)
        self.assertEqual(Unit.one(1).retrieve().delete(), 1)
        self.assertEqual(len(Unit.many()), 0)
        self.assertEqual(len(Test.many()), 0)

        [cursor.execute(statement) for statement in Plain.define()]

        plain = Plain().create()
        self.assertRaisesRegex(relations.ModelError, "plain: nothing to delete from", plain.delete)
