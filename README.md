# nested-object-cleaner

Python tool to clean unused items from a nested object.

## Background & Use Cases

### What is a nested object?

Here the term "nested objects" refers to Python lists or dictionaries that contain 
themselves one or more levels of dictionaries, such as
[JSON](https://en.wikipedia.org/wiki/JSON) objects (where dictionaries are 
represented by 'objects' and lists by 'arrays').

An example, in JSON, could look like this:

```json
{
  "importantListOfDicts": [
    {
      "name": "dict01",
      "criticalConfiguration": {
        "enableFoo": false,
        "linkedImportantDict": [
          {
            "name": "dict03",
            "bar": 123
          }
        ]
      }
    },
    {
      "name": "dict02",
      "criticalConfiguration": {
        "enableFoo": true,
        "linkedImportantDict": [
          {
            "name": "dict03",
            "bar": -45.6
          }
        ]
      }
    },
    {
      "name": "dict03",
      "criticalConfiguration": {
        "enableFoo": true,
        "linkedImportantDict": []
      }
    }
  ],
  "importantOtherDict": {
    "all": "right!",
    "useConfigsname": [
      {
        "sourceName": "dict02"
      },
      {
        "sourceName": "dict03"
      }
    ]
  }
}
```

### When to use this tool?

JSON is often used as a tool to configure more or less complex settings, for 
instance via a configuration file that complies to the JSON syntax. In such cases, 
the configuration (i.e., JSON object) may contain references between its objects 
where some object is referenced elsewhere by an identifier key-value pairing. 
Particularly in larger nested objects that grow over time such dependencies quickly 
become hard to trace, and it may happen that deprecated, i.e., no longer 
referenced objects remain in the code. This clutters the configuration, making it 
harder to maintain and possibly even cause performance issues. In these cases, it 
may be useful to remove such orphaned objects from the code - which is what this tool
is for.

For instance, in the example above, the `importanListOfDicts`'s third element (where 
`"name" == "dict03"`) may be referenced in other elements' `criticalConfiguration` 
as a `linkedImportantDict`: in the first two elements of `importanListOfDicts`, as 
well as in `importantOtherDict.useConfigFrom`.

The second element is also referenced elsewhere in the JSON: in `importantOtherDict.
useConfigFrom`. The first element, however, is _not_ referenced anywhere else and may 
therefore be "orphaned" (depending on the actual purpose of the configuration, of 
course; it may well be a valid configuration that is not automatically obsolete when 
it's not referenced elsewhere in the JSON). While this may still be spotted 
relatively easily in this case, for a sufficiently large nested object, manually 
spotting and removing orphaned items quickly becomes a challenging and error-prone 
process.

## Usage

