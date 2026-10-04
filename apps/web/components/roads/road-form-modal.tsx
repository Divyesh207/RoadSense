"use client";

import React, { useState } from "react";
import { Route, X } from "lucide-react";
import { api } from "@/lib/api-client";
import { Road, RoadCreatePayload } from "@/types/api";

// The API stores road_type as free text; these are the values its schema documents.
const ROAD_TYPES = ["HIGHWAY", "ARTERIAL", "URBAN", "RURAL", "LOCAL"] as const;
const TRAFFIC_CLASSES = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"] as const;

const inputClass =
  "w-full h-10 bg-ri-input border border-ri-line rounded-xl px-3 text-xs text-ri-text placeholder:text-ri-faint focus:outline-none focus:border-ri-primary";
const labelClass = "font-label-sm text-xs text-ri-muted font-semibold";

interface RoadFormModalProps {
  onClose: () => void;
  onCreated: (road: Road) => void;
}

/** Creates a road through POST /roads. Only fields the API accepts are offered. */
export function RoadFormModal({ onClose, onCreated }: RoadFormModalProps) {
  const [name, setName] = useState("");
  const [roadCode, setRoadCode] = useState("");
  const [roadType, setRoadType] = useState("");
  const [area, setArea] = useState("");
  const [description, setDescription] = useState("");
  const [trafficClass, setTrafficClass] = useState("");
  const [trafficAadt, setTrafficAadt] = useState("");
  const [trafficSource, setTrafficSource] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!name.trim()) return setError("Road name is required.");
    if (trafficAadt && (!/^\d+$/.test(trafficAadt) || Number(trafficAadt) > 1_000_000)) {
      return setError("Traffic count must be a whole number of vehicles per day (at most 1,000,000).");
    }
    if ((trafficClass || trafficAadt) && !trafficSource.trim()) {
      return setError("Give the source of the traffic figure, or leave the traffic fields empty.");
    }

    const payload: RoadCreatePayload = { name: name.trim() };
    if (roadCode.trim()) payload.road_code = roadCode.trim();
    if (roadType) payload.road_type = roadType;
    if (area.trim()) payload.administrative_area = area.trim();
    if (description.trim()) payload.description = description.trim();
    if (trafficClass) payload.traffic_volume_class = trafficClass as RoadCreatePayload["traffic_volume_class"];
    if (trafficAadt) payload.traffic_aadt = Number(trafficAadt);
    if (trafficSource.trim()) payload.traffic_data_source = trafficSource.trim();

    setSaving(true);
    try {
      const res = await api.roads.create(payload);
      if (!res.data) throw new Error("The API returned no road.");
      onCreated(res.data);
    } catch (err: any) {
      setError(err?.message || "The road could not be created.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-[2000]">
      <div className="bg-ri-surface border border-ri-line rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-ri-line pb-3">
          <div className="flex items-center gap-2">
            <Route className="h-5 w-5 text-ri-primary" />
            <h3 className="font-headline-sm text-base font-bold text-ri-text">Add Road</h3>
          </div>
          <button onClick={onClose} aria-label="Close" className="text-ri-muted hover:text-ri-text p-1">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5">
            <label className={labelClass}>Road name *</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={255}
              required
              placeholder="Official road name"
              className={inputClass}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className={labelClass}>Road code</label>
              <input
                value={roadCode}
                onChange={(e) => setRoadCode(e.target.value)}
                maxLength={100}
                placeholder="Route reference"
                className={inputClass}
              />
            </div>
            <div className="space-y-1.5">
              <label className={labelClass}>Classification</label>
              <select value={roadType} onChange={(e) => setRoadType(e.target.value)} className={inputClass}>
                <option value="">Not set</option>
                {ROAD_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className={labelClass}>Administrative area</label>
            <input
              value={area}
              onChange={(e) => setArea(e.target.value)}
              maxLength={150}
              placeholder="District or ward"
              className={inputClass}
            />
          </div>

          <div className="space-y-1.5">
            <label className={labelClass}>Description</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-ri-input border border-ri-line rounded-xl p-3 text-xs text-ri-text placeholder:text-ri-faint focus:outline-none focus:border-ri-primary"
            />
          </div>

          <div className="rounded-xl border border-ri-line bg-ri-input/60 p-3 space-y-3">
            <p className="text-[11px] text-ri-muted">
              Documented traffic (optional). Leave empty if there is no documented source; traffic is never estimated.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className={labelClass}>Traffic class</label>
                <select value={trafficClass} onChange={(e) => setTrafficClass(e.target.value)} className={inputClass}>
                  <option value="">Unknown</option>
                  {TRAFFIC_CLASSES.map((t) => (
                    <option key={t} value={t}>
                      {t.replace("_", " ")}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className={labelClass}>Vehicles per day (AADT)</label>
                <input
                  value={trafficAadt}
                  onChange={(e) => setTrafficAadt(e.target.value)}
                  inputMode="numeric"
                  className={inputClass}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className={labelClass}>Traffic data source</label>
              <input
                value={trafficSource}
                onChange={(e) => setTrafficSource(e.target.value)}
                maxLength={255}
                placeholder="Survey or document the figure comes from"
                className={inputClass}
              />
            </div>
          </div>

          <p className="text-[11px] text-ri-faint">
            After the road is created, add its segments. Inspections are recorded against a road and, optionally, a segment.
          </p>

          {error && (
            <p className="text-xs px-3 py-2 rounded-xl border border-ri-danger/40 bg-ri-danger/10 text-ri-danger-soft">{error}</p>
          )}

          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="h-10 px-4 rounded-xl bg-ri-raised border border-ri-line text-xs font-semibold text-ri-muted hover:text-ri-text"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="h-10 px-5 rounded-xl bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary text-xs font-bold disabled:opacity-50"
            >
              {saving ? "Creating..." : "Create Road"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
