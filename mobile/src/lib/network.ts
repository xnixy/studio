type Listener = (online: boolean) => void;

let online = true;
const listeners = new Set<Listener>();

function emit(next: boolean) {
  if (online === next) return;
  online = next;
  listeners.forEach((l) => l(online));
}

export function markNetworkOnline() {
  emit(true);
}

export function markNetworkOffline() {
  emit(false);
}

export function isNetworkOnline() {
  return online;
}

export function subscribeNetwork(listener: Listener) {
  listeners.add(listener);
  listener(online);
  return () => {
    listeners.delete(listener);
  };
}
