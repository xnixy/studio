import { useEffect, useState } from "react";
import { isNetworkOnline, subscribeNetwork } from "../lib/network";

/** Follows API reachability, not just the radio. A captive Wi-Fi still counts as offline. */
export function useOnlineStatus() {
  const [online, setOnline] = useState(isNetworkOnline);
  useEffect(() => subscribeNetwork(setOnline), []);
  return online;
}
