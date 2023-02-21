// A test file is called a spec. Each spec consists of one or more it blocks inside 0
// or more describe blocks. An it block is a single test, and a describe block is a group
// of tests.

describe("My first test", () => {
  // beforeEach is a hook that runs a function before each test in this group of tests.
  beforeEach(() => {
    // cy.log() is a command that prints text to the Cypress command log.
    cy.log("Running a test");
  });

  it("Allows the user to disable and enable the sidebar", () => {
    // cy.visit() changes the browser location.
    cy.visit("https://eecs485.org");

    // cy.contains() queries the DOM for elements with specific text. It implicitly asserts that
    // the text appears on the page; if the text doesn't exist, it will throw an error.
    //
    // We also *chain* a command here: once Cypress gives us the element(s) we queried for, we
    // make an assertion on it. Here we assert that the element containing "Files" is visible.
    cy.contains("Files").should("be.visible");

    // cy.get() also queries the DOM, but it's more flexible. It can search based on any selector,
    // similar to CSS and JQuery selectors. Here we query for an element with its `id` attribute
    // set to "left-sidebar-toggle". If no such element exists, we'll get an error. If it does
    // exist, we click it.
    cy.get("#left-sidebar-toggle").click();

    // Now we assert that the element containing "Files" is no longer visible.
    cy.contains("Files").should("not.be.visible");

    // Click the button again.
    cy.get("#left-sidebar-toggle").click();

    // Assert that "Files" is visible again!
    cy.contains("Files").should("be.visible");
  });
});
