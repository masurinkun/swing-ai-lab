(() => {
  const toggle = document.querySelector(".nav-toggle");
  const navigation = document.querySelector(".site-nav");

  if (toggle && navigation) {
    toggle.addEventListener("click", () => {
      const isOpen = navigation.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(isOpen));
    });

    navigation.addEventListener("click", (event) => {
      if (event.target instanceof HTMLAnchorElement) {
        navigation.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  const search = document.querySelector("[data-filter-search]");
  const filterButtons = [...document.querySelectorAll("[data-filter]")];
  const items = [...document.querySelectorAll(".filter-item")];
  const emptyMessage = document.querySelector(".filter-empty");
  let activeStatus = "all";

  const applyFilters = () => {
    const query = search instanceof HTMLInputElement ? search.value.trim().toLowerCase() : "";
    let visibleCount = 0;

    items.forEach((item) => {
      const matchesQuery = !query || (item.dataset.search || "").includes(query);
      const matchesStatus = activeStatus === "all" || item.dataset.status === activeStatus;
      const visible = matchesQuery && matchesStatus;
      item.hidden = !visible;
      if (visible) visibleCount += 1;
    });

    document.querySelectorAll(".recommendation-group").forEach((group) => {
      const visibleItems = group.querySelectorAll(".filter-item:not([hidden])");
      group.hidden = visibleItems.length === 0;
    });

    if (emptyMessage) emptyMessage.hidden = visibleCount !== 0;
  };

  if (search) search.addEventListener("input", applyFilters);

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activeStatus = button.dataset.filter || "all";
      filterButtons.forEach((candidate) => candidate.classList.toggle("is-active", candidate === button));
      applyFilters();
    });
  });
})();
