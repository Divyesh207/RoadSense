"use client";

import React, { useState } from "react";
import { Route, X } from "lucide-react";
import { api } from "@/lib/api-client";
import { Road, RoadCreatePayload } from "@/types/api";

// The API stores road_type as free text; these are the values its schema documents.
const ROAD_TYPES = ["HIGHWAY", "ARTERIAL", "URBAN", "RURAL", "LOCAL"] as const;
const TRAFFIC_CLASSES = ["LOW", "MEDIUM", "HIGH", "VERY_HIGH"] as const;

const inputClass =
  "w-full h-10 bg-[#151B2A] border border-[#26344F] rounded-xl px-3 text-xs text-[#F1F5F9] placeholder:text-[#64748B] focus:outline-none focus:border-[#06B6D4]";
const labelClass = "font-label-sm text-xs text-[#94A3B8] font-semibold";

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
      <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl max-h-[92vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-[#26344F] pb-3">
          <div className="flex items-center gap-2">
            <Route className="h-5 w-5 text-[#06B6D4]" />
            <h3 className="font-headline-sm text-base font-bold text-[#F1F5F9]">Add Road</h3>
          </div>
          <button onClick={onClose} aria-label="Close" className="text-[#94A3B8] hover:text-[#F1F5F9] p-1">
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
              className="w-full bg-[#151B2A] border border-[#26344F] rounded-xl p-3 text-xs text-[#F1F5F9] placeholder:text-[#64748B] focus:outline-none focus:border-[#06B6D4]"
            />
          </div>

          <div className="rounded-xl border border-[#26344F] bg-[#151B2A]/60 p-3 space-y-3">
            <p className="text-[11px] text-[#94A3B8]">
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

          <p className="text-[11px] text-[#64748B]">
            After the road is created, add its segments. Inspections are recorded against a road and, optionally, a segment.
          </p>

          {error && (
            <p className="text-xs px-3 py-2 rounded-xl border border-[#EF4444]/40 bg-[#EF4444]/10 text-[#FFB4AB]">{error}</p>
          )}

          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="h-10 px-4 rounded-xl bg-[#17223A] border border-[#26344F] text-xs font-semibold text-[#94A3B8] hover:text-[#F1F5F9]"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="h-10 px-5 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] text-xs font-bold disabled:opacity-50"
            >
              {saving ? "Creating..." : "Create Road"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
