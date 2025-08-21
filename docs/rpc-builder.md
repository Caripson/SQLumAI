# RPC Builder (Experimental)

The RPC builder constructs a best‑effort TDS RPC request payload for a limited set of types. It is intended for controlled tests, not production encoding.

Supported types
- NVARCHAR: UTF‑16LE data with a default collation blob.
- INT: 32‑bit signed.
- BIT: 0/1.

Files
- Builder: `src/tds/rpc_build.py`
- Param type map loader: `src/tds/rpc_types.py`
- Config example: `config/rpc_param_types.json`

Config and flags
- `RPC_REPACK_BUILDER=true`: enable rebuilding RPC payload after in‑place autocorrect.
- `RPC_PARAM_TYPES_PATH`: optional path to a JSON map `{ "proc": { "Param": "nvarchar|int|bit" } }`.
- `RPC_AUTOCORRECT_INPLACE=true|false`: in‑place rewrite when normalized NVARCHAR fits (pad/truncate guarded by `RPC_TRUNCATE_ON_AUTOCORRECT`).

Limitations
- Not a full TDS implementation; metadata and collation are simplified.
- Only procedure name + positional named parameters; no TVPs, decimals, dates, or nulls.
- Use for demos and CI smoke tests; for production, integrate a proper TDS library or extend the encoder.

Example map (config/rpc_param_types.json)
```json
{
  "dbo.UpdateCustomer": {
    "CustomerId": "int",
    "Phone": "nvarchar",
    "IsActive": "bit"
  }
}
```
