import React from "react";

// liekebutton
export default function likeButton(props) {
  const { lognameLikesThis, changeLikes } = props;
  let buttonText;
  if (lognameLikesThis === true) {
    buttonText = "unlike";
  } else {
    buttonText = "like";
  }
  return (
    <button type="button" style={{border:'thin'}} className="like-unlike-button" onClick={changeLikes}>
      {buttonText}
    </button>
  );
}
